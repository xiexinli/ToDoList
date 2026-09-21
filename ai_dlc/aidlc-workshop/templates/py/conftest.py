"""tests/conftest.py 模板：注册 AC marker + 常用 fixture。复制到项目 tests/ 下按需删改。

pyproject.toml 需包含：
[tool.pytest.ini_options]
markers = ["ac(id): EARS acceptance criterion id", "live: 需要真实外部服务（LLM/网络），默认不跑"]
testpaths = ["tests"]
addopts = "-m 'not live'"
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def materials() -> Path:
    """客户材料目录（只读）。"""
    return ROOT / "materials"


@pytest.fixture(scope="session")
def samples() -> Path:
    """小组自造的样本：脏数据、小基线、对话样例等。"""
    return ROOT / "samples"


@pytest.fixture
def out_dir(tmp_path: Path) -> Path:
    """每个测试独立的输出目录，断言读回文件内容而不是日志。"""
    d = tmp_path / "out"
    d.mkdir()
    return d
