"""
Cog predictor: wraps DepthFlow to turn one scene image into a depth-based
parallax video. See CLAUDE.md: Motion -- the actual differentiator.

API confirmed from DepthFlow's own examples/presets.py (BrokenSource/
DepthFlow on GitHub) -- not guessed. HorizontalPan below mirrors their
"Horizontal" preset (simple left-right parallax), matching the brief's
"simulated camera pan" requirement.
"""
import math

from attrs import define
from cog import BasePredictor, Input, Path as CogPath
from depthflow.scene import DepthScene


@define
class HorizontalPan(DepthScene):
    def update(self):
        self.state.offset = (0.80 * math.sin(self.cycle), 0.0)
        self.state.isometric = 0.60
        self.state.steady = 0.30


class Predictor(BasePredictor):
    def setup(self):
        pass  # DepthFlow loads its depth-estimation model lazily on first use

    def predict(
        self,
        image: CogPath = Input(description="Input scene image to animate"),
        duration: float = Input(
            description="Video duration in seconds", default=5.0, ge=1.0, le=15.0
        ),
    ) -> CogPath:
        scene = HorizontalPan(backend="headless")
        scene.input(image=str(image))

        output_path = "/tmp/output.mp4"
        scene.main(output=output_path, time=duration)

        return CogPath(output_path)
