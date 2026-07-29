import os
import pytest
from utils.c64_graphics_extractor import (
    decode_sprite_hires,
    decode_sprite_multicolor,
    decode_charset_char,
    generate_synthetic_sprite_data,
    generate_synthetic_char_data
)
from agent.multimodal_rag import MultimodalRAG

def test_graphics_decoding():
    # Test hires sprite decoding
    data = generate_synthetic_sprite_data("balloon")
    img = decode_sprite_hires(data)
    assert img.size == (24, 21)

    # Test multicolor sprite decoding
    mc_data = generate_synthetic_sprite_data("alien")
    img_mc = decode_sprite_multicolor(mc_data)
    assert img_mc.size == (24, 21)

    # Test charset char decoding
    char_data = generate_synthetic_char_data()
    img_char = decode_charset_char(char_data)
    assert img_char.size == (8, 8)

def test_multimodal_rag():
    rag = MultimodalRAG(assets_dir="data/assets_test", metadata_file="data/assets_test/metadata.json")

    # Check registration and search
    rag.register_asset(
        asset_id="test_balloon",
        name="Test Balloon",
        asset_type="sprite",
        mode="hires",
        dimensions="24x21",
        filepath="data/assets_test/sprite_balloon.png",
        description="Test description"
    )

    results = rag.search_assets("test")
    assert len(results) >= 1
    assert results[0]["id"] == "test_balloon"

    # Clean up test files
    if os.path.exists("data/assets_test/metadata.json"):
        os.remove("data/assets_test/metadata.json")
    if os.path.exists("data/assets_test"):
        import shutil
        shutil.rmtree("data/assets_test")
