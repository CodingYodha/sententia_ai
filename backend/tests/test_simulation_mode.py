"""
Unit & Integration Tests for Investor Simulation Mode
"""

import pytest
from pathlib import Path

from app.schemas.intake import ScenarioCreate
from app.services.simulation_service import (
    _get_simulation_folder,
    _load_asset,
    is_simulation_triggered,
    generate_simulated_structure,
)


def test_simulation_folder_location():
    folder = _get_simulation_folder()
    assert folder.exists()
    assert folder.is_dir()


def test_simulation_asset_loading():
    content = _load_asset("diagram1.mmd")
    assert "flowchart" in content or "graph" in content
    assert "Meridian" in content or "MGF" in content


def test_simulation_trigger_matching():
    scenario_us_india = ScenarioCreate(
        capital_origin="USA",
        target_jurisdiction="India",
        sector="Education (K-12)",
        investment_amount_usd=3000000.0,
        investment_structure_type="spv_layered",
        notes="Project Ananta PropCo-OpCo Model",
    )
    assert is_simulation_triggered(scenario_us_india, "auto") is True
    assert is_simulation_triggered(scenario_us_india, "true") is True
    assert is_simulation_triggered(scenario_us_india, "false") is False


@pytest.mark.asyncio
async def test_generate_simulated_structure():
    scenario = ScenarioCreate(
        capital_origin="USA",
        target_jurisdiction="India",
        sector="Education",
        investment_amount_usd=3000000.0,
        investment_structure_type="spv_layered",
    )

    # Call with 0 delay for fast unit test execution
    response = await generate_simulated_structure(scenario, delay_seconds=0.0)

    assert response.recommended_alternative_rank == 1
    assert len(response.alternatives) == 3
    assert len(response.reasoning_steps) >= 5
    assert response.proposed_timeline is not None
    assert "diagram1.mmd" in _load_asset("diagram1.mmd") or response.alternatives[0].mermaid_diagram
