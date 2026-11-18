from pathlib import Path

from sadu.modules.assistant.domain.skills import Skill, parse_skill

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"


def load_skills(directory: Path = SKILLS_DIR) -> tuple[Skill, ...]:
    paths = sorted(directory.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"No skill files in {directory}")
    skills = []
    for path in paths:
        try:
            skills.append(parse_skill(path.read_text(encoding="utf-8")))
        except ValueError as error:
            raise ValueError(f"{path.name}: {error}") from error
    return tuple(skills)
