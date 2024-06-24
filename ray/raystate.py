from typing import List

import yaml
from pydantic import BaseModel
from ray.dashboard.modules.serve.sdk import ServeSubmissionClient
from ray.serve.schema import (
    DeploymentSchema,
    RayActorOptionsSchema,
    ServeApplicationSchema,
    ServeDeploySchema,
)

from .deployments.model import ModelDeploymentArgs
from .deployments.request import RequestDeploymentArgs
import urllib.parse


class ServiceConfigurationSchema(BaseModel):
    class ModelConfigurationSchema(BaseModel):
        model_key: str
        cuda_memory_MB: int
        num_replicas: int

    model_import_path: str
    request_import_path: str
    request_num_replicas: int

    models: List[ModelConfigurationSchema]


class RayState:

    def __init__(
        self,
        ray_config_path: str,
        service_config_path: str,
        ray_dashboard_url: str,
        database_url: str,
        api_url: str,
    ) -> None:

        self.ray_dashboard_url = ray_dashboard_url
        self.database_url = database_url
        self.api_url = api_url

        with open(ray_config_path, "r") as file:
            self.ray_config = ServeDeploySchema(**yaml.safe_load(file))

        with open(service_config_path, "r") as file:
            self.service_config = ServiceConfigurationSchema(**yaml.safe_load(file))

        self.add_request_app()

        for model_config in self.service_config.models:
            self.add_model_app(model_config)

    def apply(self) -> None:

        ServeSubmissionClient(self.ray_dashboard_url).deploy_applications(
            self.ray_config.dict(exclude_unset=True),
        )

    def add_request_app(self) -> None:
        application = ServeApplicationSchema(
            name="Request",
            import_path=self.service_config.request_import_path,
            route_prefix="/request",
            deployments=[
                DeploymentSchema(
                    name="RequestDeployment",
                    num_replicas=self.service_config.request_num_replicas,
                    ray_actor_options=RayActorOptionsSchema(num_cpus=1),
                )
            ],
            args=RequestDeploymentArgs(
                ray_dashboard_url=self.ray_dashboard_url,
                api_url=self.api_url,
                database_url=self.database_url,
            ).model_dump(),
        )

        self.ray_config.applications.append(application)

    def add_model_app(
        self, model_config: ServiceConfigurationSchema.ModelConfigurationSchema
    ) -> None:
        
        model_key = urllib.parse.quote(model_config.model_key, safe='')

        application = ServeApplicationSchema(
            name=f"Model:{model_key}",
            import_path=self.service_config.model_import_path,
            route_prefix=f"/model:{model_key}",
            deployments=[
                DeploymentSchema(
                    name="ModelDeployment",
                    num_replicas=model_config.num_replicas,
                    ray_actor_options=RayActorOptionsSchema(
                        resources={"cuda_memory_MB": model_config.cuda_memory_MB}
                    ),
                )
            ],
            args=ModelDeploymentArgs(
                model_key=model_config.model_key,
                api_url=self.api_url,
                database_url=self.database_url,
            ).model_dump(),
        )

        self.ray_config.applications.append(application)
