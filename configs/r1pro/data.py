# =============================================================================
# Robot Config template.
#
# Copy this directory, then replace every placeholder in angle brackets:
#
#     cp -r configs/_template configs/my_task
#     grep -rn 'YOUR_' configs/my_task     # your checklist
#
# Nothing here resolves until they are gone. That is deliberate: a template that
# appeared to work would invite you to leave a field unchanged and train against
# the wrong column.
#
# This file must stay in the same directory as its YAML. train.py imports
# <yaml_dir>/data.py by path so the @register_config below fires, and derives
# state_dim / action_dim / action_horizon from the config it registers.
#
# =============================================================================
from __future__ import annotations

import os

# Your robot's adapter class.
from tau0_vla.adapters.r1pro.layout import R1ProRobot
from tau0_vla.data import FrameFilter, PromptSource, register_config
from tau0_vla.data.modalities import ArmJoint, Gripper, Image, Prompt
from tau0_vla.data.modalities.image import ColorJitter, ResizeWithPad

# Set TAU0_DATA_ROOT to point at your data without editing this file.
_DATA_ROOT = os.environ.get("TAU0_DATA_ROOT", "/data/behavior_2026")

# One entry per LeRobot v3.0 repo. They must share a modality schema — same
# columns, same cameras — because one Robot Config describes all of them.
_REPOS = [
    f"{_DATA_ROOT}/r1pro_train",
]

# Written by scripts/norm_stats/merge_stats.py, which takes this path as --out.
# The two have to agree.
_NORM_STATS = f"{_DATA_ROOT}/norm_stats/behavior-r1pro-unified-40d.json"


# Prefixed to every sample's task text. Stating embodiment and control mode
# explicitly lets one checkpoint serve several of both.
def _robot_prompt(robot_type: str, control_mode: str, *, wbc: bool) -> str:
    head = (
        "You are controlling a robot.\n"
        f"Robot type: {robot_type}\n"
        f"Control mode: {control_mode}\n"
        f"Whole-body control: {'enabled' if wbc else 'disabled'}\n"
    )
    return head + "Task: {instruction}"


# ColorJitter draws per sample; ResizeWithPad preserves aspect ratio. The size
# here has to match max_pixels in the YAML.
_IMAGE_TRANSFORMS = [
    ColorJitter(prob=0.33, brightness=0.3, contrast=0.4, saturation=0.5, hue=0.03),
    ResizeWithPad(224, 224),
]

# One Image per camera, named as your dataset names it. The YAML's camera_keys
# must list the same names.
_IMAGES = [
    Image("head", transforms=_IMAGE_TRANSFORMS),
    Image("wrist", transforms=_IMAGE_TRANSFORMS),
]

# Which annotation tracks decide whether a frame can be an anchor. Drop labels
# your dataset does not carry — see DATASET_FORMAT.md.
_FRAME_FILTER = FrameFilter(positive=["l3"], negative=["error_frame"])

_ARGS = dict(
    repo_id=_REPOS,
    images=_IMAGES,
    # Mix a fixed instruction with the dataset's own per-segment text. Use
    # PromptSource.fix(...) alone if your dataset has no l2/l3 annotations.
    prompt_source=PromptSource.random(
        [
            PromptSource.fix("Complete the BEHAVIOR 2026 task."),
            PromptSource.from_label(source="l2"),
        ],
        probabilities=[0.2, 0.8],
    ),
    frame_filter=_FRAME_FILTER,
    prompt=Prompt(template=_robot_prompt("R1Pro", "joint", wbc=False)),
    # action_horizon is the chunk length the model predicts. The other two are
    # the Unified Layout width and should stay at 40.
    action_horizon=30,
    state_padding_dim=40,
    action_padding_dim=40,
    return_all_norm_forms=True,
)


# The function name IS the config name, and the YAML's data_args.config_name has
# to match it. Rename it to yours (underscores normalize to dashes when
# save_norm_stats derives a filename from it).
@register_config
def behavior_r1pro() -> R1ProRobot:
    return R1ProRobot(
        # A unified route scatters into the 40D layout and normalizes from
        # per_embodiment[<registry_key>], so these entries only declare which
        # modality is present — normalize="none" is correct here.
        state=[ArmJoint(normalize="none"), Gripper(normalize="none")],
        action=[ArmJoint(normalize="none"), Gripper(normalize="none")],
        norm_stats_path=_NORM_STATS,
        **_ARGS,
    )