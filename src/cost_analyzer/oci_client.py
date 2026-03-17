"""OCI API client wrapper with auto-detected authentication."""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import oci

from cost_analyzer.config import get_settings
from cost_analyzer.models import CostLineItem

if TYPE_CHECKING:
    from oci.usage_api.models import Filter

logger = logging.getLogger("cost_analyzer.oci_client")


class OCIClient:
    """Wrapper around OCI SDK clients with auto-detected authentication."""

    def __init__(self) -> None:
        settings = get_settings()
        self._config, self._signer = self._create_auth(settings)
        self._tenancy_id = settings.oci_tenancy_id or self._config.get("tenancy")
        self._compartment_id = settings.oci_compartment_id or self._tenancy_id

        # Usage API はホームリージョンでのみ実行可能
        usage_config = dict(self._config)
        if settings.oci_home_region:
            usage_config["region"] = settings.oci_home_region
        self._usage_client = oci.usage_api.UsageapiClient(
            config=usage_config,
            signer=self._signer,
            retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
        )
        self._genai_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
            config=self._config,
            signer=self._signer,
            service_endpoint=settings.oci_genai_endpoint,
            retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
        )

    @staticmethod
    def _create_auth(settings) -> tuple[dict, oci.signer.Signer | oci.auth.signers.InstancePrincipalsSecurityTokenSigner]:  # noqa: E501
        """Create OCI config and signer based on auth type."""
        if settings.oci_auth_type == "instance_principal":
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            config = {"tenancy": settings.oci_tenancy_id} if settings.oci_tenancy_id else {}
            return config, signer

        config = oci.config.from_file(
            file_location=settings.oci_config_file,
            profile_name=settings.oci_config_profile,
        )
        signer = oci.signer.Signer(
            tenancy=config["tenancy"],
            user=config["user"],
            fingerprint=config["fingerprint"],
            private_key_file_location=config.get("key_file"),
            pass_phrase=config.get("pass_phrase"),
        )
        return config, signer

    @property
    def genai_client(self) -> oci.generative_ai_inference.GenerativeAiInferenceClient:
        """Get the GenAI inference client."""
        return self._genai_client

    @property
    def compartment_id(self) -> str:
        """Get the compartment ID for GenAI calls."""
        return self._compartment_id

    @staticmethod
    def build_filter(
        service_filter: str | None = None,
        compartment_filter: str | None = None,
    ) -> Filter | None:
        """service_filter / compartment_filter から OCI Filter オブジェクトを構築する。

        Args:
            service_filter: サービス名でフィルタリング（例: "COMPUTE"）。
            compartment_filter: コンパートメント名でフィルタリング。

        Returns:
            OCI Filter オブジェクト。フィルタ条件がなければ None。
        """
        dimensions: list = []
        if service_filter is not None:
            dimensions.append(
                oci.usage_api.models.Dimension(key="service", value=service_filter)
            )
        if compartment_filter is not None:
            dimensions.append(
                oci.usage_api.models.Dimension(key="compartmentName", value=compartment_filter)
            )
        if not dimensions:
            return None

        operator = "AND" if len(dimensions) > 1 else "AND"
        return oci.usage_api.models.Filter(
            operator=operator,
            dimensions=dimensions,
        )

    def request_cost_data(
        self,
        start_date: date,
        end_date: date,
        granularity: str = "DAILY",
        filter: Filter | None = None,
        service_filter: str | None = None,
        compartment_filter: str | None = None,
    ) -> list[CostLineItem]:
        """Fetch cost data from OCI Usage API.

        Args:
            start_date: Query period start (inclusive).
            end_date: Query period end (exclusive).
            granularity: DAILY, MONTHLY, or TOTAL.
            filter: Optional OCI Filter for service/compartment filtering.
            service_filter: サービス名フィルタ（filter が None の場合に使用）。
            compartment_filter: コンパートメント名フィルタ（filter が None の場合に使用）。

        Returns:
            List of CostLineItem models.
        """
        # filter が明示指定されていなければ service_filter / compartment_filter から構築
        if filter is None:
            filter = self.build_filter(service_filter, compartment_filter)

        details = oci.usage_api.models.RequestSummarizedUsagesDetails(
            tenant_id=self._tenancy_id,
            time_usage_started=datetime.combine(start_date, datetime.min.time()),
            time_usage_ended=datetime.combine(end_date, datetime.min.time()),
            granularity=granularity,
            query_type="COST",
            group_by=["service", "currency"],
        )
        if filter is not None:
            details.filter = filter

        logger.info(
            "Requesting cost data",
            extra={"extra_data": {
                "start": str(start_date),
                "end": str(end_date),
                "granularity": granularity,
            }},
        )

        response = oci.pagination.list_call_get_all_results(
            self._usage_client.request_summarized_usages,
            details,
        )

        items = []
        # list_call_get_all_results returns Response with data as list
        summaries = response.data if isinstance(response.data, list) else response.data.items
        for summary in summaries:
            if summary.computed_amount is None:
                continue
            items.append(
                CostLineItem(
                    service=summary.service or "UNKNOWN",
                    amount=Decimal(str(summary.computed_amount)),
                    currency=summary.currency or "USD",
                    compartment_name=summary.compartment_name,
                    compartment_path=summary.compartment_path,
                    time_usage_started=summary.time_usage_started,
                    time_usage_ended=summary.time_usage_ended,
                )
            )
        logger.info(
            "Cost data received",
            extra={"extra_data": {"item_count": len(items)}},
        )
        return items

    def get_available_services(self) -> list[str]:
        """利用可能なサービス名の一覧を取得する。

        UsageapiClient.request_summarized_configurations() を使用して
        OCI テナンシーで利用可能なサービスを返す。

        Returns:
            サービス名のリスト。
        """
        details = oci.usage_api.models.RequestSummarizedUsagesDetails(
            tenant_id=self._tenancy_id,
            time_usage_started=datetime.combine(date.today(), datetime.min.time()),
            time_usage_ended=datetime.combine(date.today(), datetime.min.time()),
            granularity="DAILY",
            query_type="COST",
        )
        response = self._usage_client.request_summarized_configurations(
            details,
        )
        services: list[str] = []
        for config in response.data.items:
            if config.key == "service" and config.values:
                services.extend(config.values)
        logger.info(
            "利用可能なサービスを取得",
            extra={"extra_data": {"count": len(services)}},
        )
        return services

    def get_available_compartments(self) -> list[str]:
        """利用可能なコンパートメント名の一覧を取得する。

        UsageapiClient.request_summarized_configurations() を使用して
        OCI テナンシーで利用可能なコンパートメントを返す。

        Returns:
            コンパートメント名のリスト。
        """
        details = oci.usage_api.models.RequestSummarizedUsagesDetails(
            tenant_id=self._tenancy_id,
            time_usage_started=datetime.combine(date.today(), datetime.min.time()),
            time_usage_ended=datetime.combine(date.today(), datetime.min.time()),
            granularity="DAILY",
            query_type="COST",
        )
        response = self._usage_client.request_summarized_configurations(
            details,
        )
        compartments: list[str] = []
        for config in response.data.items:
            if config.key == "compartmentName" and config.values:
                compartments.extend(config.values)
        logger.info(
            "利用可能なコンパートメントを取得",
            extra={"extra_data": {"count": len(compartments)}},
        )
        return compartments
