from dataclasses import dataclass
from enum import StrEnum

CRACK = ("crack",)
PLASTER_LOSS = ("plaster_loss",)
SALT = ("salt_efflorescence",)
SOUND: tuple[str, ...] = ()
PATCH_TAG_TYPES = frozenset({*CRACK, *PLASTER_LOSS, *SALT})
OPEN_LICENCES = frozenset({"CC BY 4.0", "MIT", "Apache-2.0"})

FolderLabels = tuple[tuple[str, tuple[str, ...] | None], ...]


class LabelKind(StrEnum):
    PATCH_TAGS = "patch_tags"
    CRACK_LINES = "crack_lines"


class HubLayout(StrEnum):
    FILES = "files"
    PARQUET_ANSWERS = "parquet_answers"


@dataclass(frozen=True)
class DirectFile:
    url: str
    archive: str


@dataclass(frozen=True)
class MendeleyFiles:
    dataset_id: str
    version: int


@dataclass(frozen=True)
class HubDataset:
    repo_id: str
    revision: str
    layout: HubLayout
    allow_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class ManualDownload:
    archive: str


Fetch = DirectFile | MendeleyFiles | HubDataset | ManualDownload


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    licence: str
    page: str
    fetch: Fetch
    label_kind: LabelKind
    folder_labels: FolderLabels = ()
    by_default: bool = True
    surface: str = ""
    cannot_teach: str = ""


SOURCES: tuple[Source, ...] = (
    Source(
        key="historical_cracks_cairo",
        title="Historical-crack18-19, Mosque of Amir Al-Maridani (1340), Cairo",
        licence="CC BY 4.0",
        page="https://data.mendeley.com/datasets/xfk99kpmj9/1",
        fetch=MendeleyFiles("xfk99kpmj9", 1),
        label_kind=LabelKind.PATCH_TAGS,
        folder_labels=(("non", SOUND), ("crack", CRACK)),
        surface="historic stone and plaster",
        cannot_teach="geometry, severity, earthen plaster",
    ),
    Source(
        key="kasbah_algiers",
        title="Surface damage of heritage walls, Kasbah of Algiers",
        licence="CC BY 4.0",
        page="https://data.mendeley.com/datasets/zwshr65gnc/2",
        fetch=MendeleyFiles("zwshr65gnc", 2),
        label_kind=LabelKind.PATCH_TAGS,
        folder_labels=(
            ("efflorescence", SALT),
            ("spall", PLASTER_LOSS),
            ("crack", CRACK),
            ("mold", None),
        ),
        surface="historic plastered masonry",
        cannot_teach="geometry, Najdi mud-brick, severity",
    ),
    Source(
        key="darbhanga_fort",
        title="Brick masonry surface damage, battledore of Darbhanga Fort",
        licence="CC BY 4.0",
        page="https://data.mendeley.com/datasets/s6t5nn73bm/1",
        fetch=MendeleyFiles("s6t5nn73bm", 1),
        label_kind=LabelKind.PATCH_TAGS,
        folder_labels=(
            ("background", SOUND),
            ("vegetation", None),
            ("spall", PLASTER_LOSS),
            ("crack", CRACK),
        ),
        surface="historic red brick masonry",
        cannot_teach="earthen plaster, severity; images not split by class are skipped",
    ),
    Source(
        key="brickwork_cracks",
        title="Brickwork Cracks Dataset",
        licence="CC BY 4.0",
        page="https://zenodo.org/records/8014150",
        fetch=DirectFile(
            "https://zenodo.org/records/8014150/files/Brickwork_cracks_dataset.zip?download=1",
            "Brickwork_cracks_dataset.zip",
        ),
        label_kind=LabelKind.PATCH_TAGS,
        folder_labels=(("non", SOUND), ("negative", SOUND), ("positive", CRACK), ("crack", CRACK)),
        surface="brickwork",
        cannot_teach="geometry, earthen plaster",
    ),
    Source(
        key="rfsat_masonry",
        title="Crack Detection in Images of Bricks and Masonry",
        licence="CC BY 4.0",
        page="https://zenodo.org/records/6870108",
        fetch=DirectFile(
            "https://zenodo.org/records/6870108/files/Dataset%20(RFSAT).zip?download=1",
            "Dataset (RFSAT).zip",
        ),
        label_kind=LabelKind.PATCH_TAGS,
        folder_labels=(("positive", CRACK), ("negative", SOUND)),
        surface="bricks and masonry",
        cannot_teach="geometry, earthen plaster",
    ),
    Source(
        key="sdnet2018",
        title="SDNET2018 concrete crack images (bridge decks, walls, pavements)",
        licence="CC BY 4.0",
        page="https://digitalcommons.usu.edu/all_datasets/48",
        fetch=DirectFile(
            "https://digitalcommons.usu.edu/cgi/viewcontent.cgi?filename=2&article=1047"
            "&context=all_datasets&type=additional",
            "SDNET2018.zip",
        ),
        label_kind=LabelKind.PATCH_TAGS,
        folder_labels=(
            ("cd", CRACK),
            ("cw", CRACK),
            ("cp", CRACK),
            ("ud", SOUND),
            ("uw", SOUND),
            ("up", SOUND),
        ),
        surface="concrete",
        cannot_teach="geometry, severity, any earthen texture",
    ),
    Source(
        key="ozgenel_classification",
        title="Concrete Crack Images for Classification (Özgenel)",
        licence="CC BY 4.0",
        page="https://data.mendeley.com/datasets/5y9wdsg2zt/2",
        fetch=MendeleyFiles("5y9wdsg2zt", 2),
        label_kind=LabelKind.PATCH_TAGS,
        folder_labels=(("positive", CRACK), ("negative", SOUND)),
        surface="concrete",
        cannot_teach="geometry, width class, mud-brick surfaces",
    ),
    Source(
        key="ozgenel_segmentation",
        title="Concrete Crack Segmentation Dataset (Özgenel)",
        licence="CC BY 4.0",
        page="https://data.mendeley.com/datasets/jwsn7tfbrp/1",
        fetch=MendeleyFiles("jwsn7tfbrp", 1),
        label_kind=LabelKind.CRACK_LINES,
        surface="concrete",
        cannot_teach="width in mm (no scale), severity",
    ),
    Source(
        key="ctcd_tunnel_cracks",
        title="Complex Tunnel Crack Dataset (CTCD), CraSAM paper",
        licence="CC BY 4.0",
        page="https://huggingface.co/datasets/shiweiluo99/tunnel-crack-segmentation-dataset",
        fetch=HubDataset(
            "shiweiluo99/tunnel-crack-segmentation-dataset",
            "d7f60e61914776221f38208d5064a0246887ef4e",
            HubLayout.FILES,
            ("*.bmp", "*.png", "*.jpg"),
        ),
        label_kind=LabelKind.CRACK_LINES,
        surface="tunnel lining concrete",
        cannot_teach="earthen texture, severity",
    ),
    Source(
        key="panam_city",
        title="Historic wall images of Panam City, Sonargaon (UNESCO tentative list)",
        licence="CC BY 4.0",
        page="https://data.mendeley.com/datasets/6h6rhwfkpy/1",
        fetch=MendeleyFiles("6h6rhwfkpy", 1),
        label_kind=LabelKind.PATCH_TAGS,
        folder_labels=(
            ("corroded pla", PLASTER_LOSS),
            ("corroded brick", None),
            ("artistic", SOUND),
            ("fungus", None),
            ("living plant", None),
        ),
        by_default=False,
        surface="historic lime-plastered brick",
        cannot_teach="cracks, salt; a 2.7 GB download, so it is opt-in",
    ),
    Source(
        key="bd3_building_defects",
        title="BD3 Building Defect Dataset (VQA copy on the Hugging Face Hub)",
        licence="unclear: the Hub card says CC BY 4.0, the original BD3 repository states none",
        page="https://huggingface.co/datasets/chandrabhuma/building_defect_vqa",
        fetch=HubDataset(
            "chandrabhuma/building_defect_vqa",
            "520fef082f3b2bf42d5301f885079f74bac839de",
            HubLayout.PARQUET_ANSWERS,
            ("data/*.parquet",),
        ),
        label_kind=LabelKind.PATCH_TAGS,
        folder_labels=(
            ("major crack", CRACK),
            ("minor crack", CRACK),
            ("peeling", PLASTER_LOSS),
            ("spalling", PLASTER_LOSS),
            ("plain", SOUND),
            ("algae", None),
            ("stain", None),
        ),
        by_default=False,
        surface="concrete and stone buildings",
        cannot_teach="earthen texture; research use only until the licence is confirmed",
    ),
)

SOURCES_BY_KEY = {source.key: source for source in SOURCES}
DEFAULT_KEYS = tuple(source.key for source in SOURCES if source.by_default)
