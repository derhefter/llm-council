"""3-stage LLM Council orchestration."""

import re
import time
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple

from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL, TITLE_MODEL
from .context import ContextBlock, build_prompt
from .profiles import DEFAULT_PROFILE, Profile, get_profile


def _resolve(profile: Optional[Profile]) -> Profile:
    return profile or get_profile(DEFAULT_PROFILE)


def _collect_stats(responses: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    """Sum tokens/cost/duration over a batch of model responses."""
    stats = {
        "calls": len(responses),
        "failed": sum(1 for r in responses.values() if r is None),
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cost": 0.0,
        "max_duration": 0.0,
    }
    for response in responses.values():
        if not response:
            continue
        usage = response.get("usage") or {}
        stats["prompt_tokens"] += usage.get("prompt_tokens") or 0
        stats["completion_tokens"] += usage.get("completion_tokens") or 0
        stats["cost"] += float(usage.get("cost") or 0.0)
        stats["max_duration"] = max(stats["max_duration"], response.get("duration") or 0.0)
    stats["cost"] = round(stats["cost"], 5)
    return stats


async def stage1_collect_responses(
    user_query: str,
    profile: Optional[Profile] = None,
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    results, _ = await stage1_collect_responses_with_stats(user_query, profile)
    return results


async def stage1_collect_responses_with_stats(
    user_query: str,
    profile: Optional[Profile] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Stage 1 variant that also returns token/cost stats."""
    profile = _resolve(profile)
    messages = [{"role": "user", "content": user_query}]
    responses = await query_models_parallel(profile.models, messages)

    stage1_results = [
        {"model": model, "response": response.get('content', '') or ''}
        for model, response in responses.items()
        if response is not None
    ]
    return stage1_results, _collect_stats(responses)


def build_ranking_prompt(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    profile: Optional[Profile] = None,
) -> Tuple[str, Dict[str, str]]:
    """Build the Stage 2 prompt and the label -> model mapping."""
    profile = _resolve(profile)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    rubric_section = f"\nEvaluation criteria:\n{profile.rubric}\n" if profile.rubric else ""

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}
{rubric_section}
Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    return ranking_prompt, label_to_model


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    profile: Optional[Profile] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    results, label_to_model, _ = await stage2_collect_rankings_with_stats(
        user_query, stage1_results, profile
    )
    return results, label_to_model


async def stage2_collect_rankings_with_stats(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    profile: Optional[Profile] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, str], Dict[str, Any]]:
    """Stage 2 variant that also returns token/cost stats."""
    profile = _resolve(profile)
    ranking_prompt, label_to_model = build_ranking_prompt(
        user_query, stage1_results, profile
    )

    messages = [{"role": "user", "content": ranking_prompt}]
    responses = await query_models_parallel(profile.models, messages)

    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '') or ''
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parse_ranking_from_text(full_text),
            })

    return stage2_results, label_to_model, _collect_stats(responses)


def build_chairman_prompt(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    profile: Optional[Profile] = None,
) -> str:
    """Build the Stage 3 synthesis prompt."""
    profile = _resolve(profile)

    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    if stage2_results:
        stage2_text = "\n\n".join([
            f"Model: {result['model']}\nRanking: {result['ranking']}"
            for result in stage2_results
        ])
        stage2_section = f"\nSTAGE 2 - Peer Rankings:\n{stage2_text}\n"
        rankings_hint = "- The peer rankings and what they reveal about response quality\n"
    else:
        stage2_section = ""
        rankings_hint = ""

    return f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question{', and then ranked each other responses' if stage2_results else ''}.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}
{stage2_section}
Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
{rankings_hint}- Any patterns of agreement or disagreement

Do not average the responses into mush. Where the council members disagree, say so and say who is right. Where they all agree, do not treat agreement as proof.

{profile.output_schema}

Answer in the language of the original question.

Provide the council's final answer now:"""


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    profile: Optional[Profile] = None,
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Returns:
        Dict with 'model' and 'response' keys
    """
    result, _ = await stage3_synthesize_final_with_stats(
        user_query, stage1_results, stage2_results, profile
    )
    return result


async def stage3_synthesize_final_with_stats(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    profile: Optional[Profile] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Stage 3 variant that also returns token/cost stats."""
    profile = _resolve(profile)
    chairman_prompt = build_chairman_prompt(
        user_query, stage1_results, stage2_results, profile
    )

    messages = [{"role": "user", "content": chairman_prompt}]
    response = await query_model(profile.chairman, messages)
    stats = _collect_stats({profile.chairman: response})

    if response is None:
        return {
            "model": profile.chairman,
            "response": "Error: Unable to generate final synthesis.",
        }, stats

    return {
        "model": profile.chairman,
        "response": response.get('content', '') or '',
    }, stats


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Returns:
        List of response labels in ranked order (empty if unparseable)
    """
    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Preferred: numbered list format, e.g. "1. Response A"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: any "Response X" patterns in order
            return re.findall(r'Response [A-Z]', ranking_section)

    # Last resort: scan the whole text
    return re.findall(r'Response [A-Z]', ranking_text)


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        parsed_ranking = ranking.get('parsed_ranking') or parse_ranking_from_text(
            ranking['ranking']
        )
        seen = set()
        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model and label not in seen:
                seen.add(label)
                model_positions[label_to_model[label]].append(position)

    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            aggregate.append({
                "model": model,
                "average_rank": round(sum(positions) / len(positions), 2),
                "rankings_count": len(positions),
            })

    aggregate.sort(key=lambda x: x['average_rank'])
    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """Generate a short title (3-5 words) for a conversation."""
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]
    response = await query_model(TITLE_MODEL, messages, timeout=30.0)

    if response is None:
        return "New Conversation"

    title = (response.get('content') or 'New Conversation').strip().strip('"\'')
    if len(title) > 50:
        title = title[:47] + "..."
    return title


async def run_full_council(
    user_query: str,
    profile: Optional[Profile] = None,
    context_blocks: Optional[List[ContextBlock]] = None,
) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete council process.

    Args:
        user_query: The user's question
        profile: Council profile (models, rubric, output schema)
        context_blocks: Optional files/diffs/repo info prepended to the question

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    profile = _resolve(profile)
    started = time.monotonic()
    composed_query = build_prompt(user_query, context_blocks, profile)

    stage1_results, s1_stats = await stage1_collect_responses_with_stats(
        composed_query, profile
    )

    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again.",
        }, {"profile": profile.name}

    stage2_results: List[Dict[str, Any]] = []
    label_to_model: Dict[str, str] = {}
    aggregate_rankings: List[Dict[str, Any]] = []
    s2_stats = {"calls": 0, "failed": 0, "prompt_tokens": 0, "completion_tokens": 0,
                "cost": 0.0, "max_duration": 0.0}

    if profile.peer_review:
        stage2_results, label_to_model, s2_stats = await stage2_collect_rankings_with_stats(
            composed_query, stage1_results, profile
        )
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    stage3_result, s3_stats = await stage3_synthesize_final_with_stats(
        composed_query, stage1_results, stage2_results, profile
    )

    metadata = {
        "profile": profile.name,
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "context_labels": [b.label for b in (context_blocks or [])],
        "run_stats": {
            "duration_s": round(time.monotonic() - started, 1),
            "cost_usd": round(s1_stats["cost"] + s2_stats["cost"] + s3_stats["cost"], 5),
            "prompt_tokens": s1_stats["prompt_tokens"] + s2_stats["prompt_tokens"] + s3_stats["prompt_tokens"],
            "completion_tokens": s1_stats["completion_tokens"] + s2_stats["completion_tokens"] + s3_stats["completion_tokens"],
            "failed_calls": s1_stats["failed"] + s2_stats["failed"] + s3_stats["failed"],
            "stages": {"stage1": s1_stats, "stage2": s2_stats, "stage3": s3_stats},
        },
    }

    return stage1_results, stage2_results, stage3_result, metadata
