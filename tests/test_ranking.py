"""Parsing model output and turning it into an aggregate ranking."""

from backend.council import calculate_aggregate_rankings, parse_ranking_from_text

LABELS = {"Response A": "m1", "Response B": "m2", "Response C": "m3"}


def test_parses_the_documented_format():
    text = "Bewertung...\n\nFINAL RANKING:\n1. Response C\n2. Response A\n3. Response B"
    assert parse_ranking_from_text(text) == ["Response C", "Response A", "Response B"]


def test_parses_an_unnumbered_ranking_section():
    text = "Bla\n\nFINAL RANKING:\nResponse B\nResponse A"
    assert parse_ranking_from_text(text) == ["Response B", "Response A"]


def test_ignores_response_mentions_before_the_ranking_header():
    text = ("Response A ist schwach, Response B ist gut.\n\n"
            "FINAL RANKING:\n1. Response B\n2. Response A")
    assert parse_ranking_from_text(text) == ["Response B", "Response A"]


def test_falls_back_to_scanning_when_the_header_is_missing():
    assert parse_ranking_from_text("Erst Response B, dann Response A") == [
        "Response B", "Response A"
    ]


def test_unparseable_output_yields_an_empty_ranking():
    assert parse_ranking_from_text("Ich rangiere nicht gerne.") == []
    assert parse_ranking_from_text("") == []


def test_aggregate_orders_by_average_position():
    stage2 = [
        {"model": "m1", "ranking": "", "parsed_ranking": ["Response C", "Response B", "Response A"]},
        {"model": "m2", "ranking": "", "parsed_ranking": ["Response C", "Response B", "Response A"]},
    ]
    result = calculate_aggregate_rankings(stage2, LABELS)

    assert [r["model"] for r in result] == ["m3", "m2", "m1"]
    assert [r["average_rank"] for r in result] == [1.0, 2.0, 3.0]
    assert all(r["rankings_count"] == 2 for r in result)


def test_a_tie_keeps_both_models_with_the_same_average():
    """Two evaluators disagreeing exactly cancel out - the tie must be visible."""
    stage2 = [
        {"model": "m1", "ranking": "", "parsed_ranking": ["Response A", "Response B"]},
        {"model": "m2", "ranking": "", "parsed_ranking": ["Response B", "Response A"]},
    ]
    result = calculate_aggregate_rankings(stage2, LABELS)

    assert {r["average_rank"] for r in result} == {1.5}
    assert len(result) == 2


def test_unknown_labels_are_ignored():
    stage2 = [{"model": "m1", "ranking": "", "parsed_ranking": ["Response Z", "Response A"]}]
    result = calculate_aggregate_rankings(stage2, LABELS)

    assert [r["model"] for r in result] == ["m1"]
    assert result[0]["average_rank"] == 2.0, "position is kept, the bad label only skipped"


def test_a_repeated_label_is_only_counted_once():
    stage2 = [{"model": "m1", "ranking": "", "parsed_ranking":
               ["Response A", "Response A", "Response B"]}]
    result = calculate_aggregate_rankings(stage2, LABELS)

    by_model = {r["model"]: r for r in result}
    assert by_model["m1"]["rankings_count"] == 1


def test_an_empty_ranking_contributes_nothing():
    stage2 = [
        {"model": "m1", "ranking": "kein Ranking", "parsed_ranking": []},
        {"model": "m2", "ranking": "", "parsed_ranking": ["Response A", "Response B"]},
    ]
    result = calculate_aggregate_rankings(stage2, LABELS)

    assert all(r["rankings_count"] == 1 for r in result), \
        "one evaluator failed, the other still counts"


def test_falls_back_to_reparsing_when_parsed_ranking_is_absent():
    stage2 = [{"model": "m1", "ranking": "FINAL RANKING:\n1. Response B\n2. Response A"}]
    result = calculate_aggregate_rankings(stage2, LABELS)

    assert [r["model"] for r in result] == ["m2", "m1"]
