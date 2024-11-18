import replicate

from .ai import Replicate, ReplicateDetails
from apps.imagination.schemas import ImagineCreateSchema


class ReplicateBackgroundRemoval(Replicate):
    def __init__(self, imagination, name) -> None:
        super().__init__(imagination, name)

    async def _request(self, **kwargs) -> ReplicateDetails:
        prediction = replicate.predictions.create(
            version=self.application_name.version,
            input={"image": self.imagination.image},
            webhook=self.imagination.webhook_url,
            webhook_events_filter=["completed"],
        )
        return await self._result_to_details(prediction)

    async def _result_to_details(self, prediction: replicate.prediction.Prediction):
        prediction_data = prediction.__dict__.copy()
        prediction_data.pop("status", None)
        prediction_data.pop("model", None)
        return ReplicateDetails(
            **prediction_data,
            prompt="",
            status=self._status(prediction.status),
            model=f"{self.application_name.owner}/{self.application_name.name}",
            result=({"uri": prediction.output} if prediction.output else None),
            percentage=100,
        )

    def validate(self, data: ImagineCreateSchema):
        imagination_valid = data.mode == "background-removal" and data.image is not None
        message = (
            "Mode must be 'background-removal'."
            if data.mode != "background-removal"
            else ("Imagination Image is required." if data.image is None else None)
        )
        return imagination_valid, message
