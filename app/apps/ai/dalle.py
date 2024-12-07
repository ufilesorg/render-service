from datetime import datetime

from openai import OpenAI
from openai.types import ImagesResponse

from .engine import Engine, EnginesDetails
from .schemas import ImaginationStatus


class Dalle(Engine):
    def __init__(self, item, **kwargs) -> None:
        super().__init__(item, **kwargs)
        if self.item:
            self.client = OpenAI(
                api_key="tpsg-CMsYsphOUwPaxzfIdoEA46aJf3Pu297",
                base_url="https://api.metisai.ir/openai/v1",
            )

    async def result(self, **kwargs) -> EnginesDetails:
        result = self.item.meta_data.get("result")
        return (
            EnginesDetails(**self.item.meta_data)
            if result
            else self._result_to_details(
                ImagesResponse(
                    created=int(datetime.now().timestamp()),
                    data=[],
                    error=f"Server error: " + self.item.meta_data.get("error")
                    or "Imagination has no meta_data",
                )
            )
        )

    async def _request(self, **kwargs) -> EnginesDetails:
        response = self.client.images.generate(
            prompt=self.item.prompt,
            n=1,
            model="dall-e-3",
            size=self._get_size(),
        )
        return self._result_to_details(response)

    def _status(self, response: ImagesResponse):
        return (
            ImaginationStatus.completed
            if len(response.data) > 0
            else ImaginationStatus.error
        )

    def _get_size(self):
        return {
            "1:1": "1024x1024",
            "7:4": "1792x1024",
            "4:7": "1024x1792",
        }.get(self.item.aspect_ratio)

    def validate(self, data):
        aspect_ratio_valid = data.aspect_ratio in self.engine.supported_aspect_ratios
        message = (
            f"aspect_ratio must be one of them {self.engine.supported_aspect_ratios}"
            if not aspect_ratio_valid
            else None
        )
        return aspect_ratio_valid, message

    def _result_to_details(self, response: ImagesResponse):
        return EnginesDetails(
            id=None,
            prompt=self.item.prompt,
            error=str(response.error) if response.error else None,
            status=self._status(response),
            result=({"uri": response.data[0].url} if len(response.data) > 0 else None),
        )
