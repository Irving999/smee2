from enum import Enum
import prometheus_client


class Metrics(Enum):
    CONNECTED_CLIENTS = (
        "connected_clients",
        "Number of connected websocket clients per subscription",
        prometheus_client.Gauge,
        ["subscription_id"],
    )

    FAILED_CONNECTIONS = (
        "failed_connections",
        "Number of failed connection attempts to /tunnel",
        prometheus_client.Counter,
        ["subscription_id", "reason"],
    )

    def __init__(self, title, description, prometheus_type, labels=()):
        self.title = title
        self.description = description
        self.prometheus_type = prometheus_type
        self.labels = labels


class MetricsHandler:
    @classmethod
    def init(cls) -> None:
        for metric in Metrics:
            setattr(
                cls,
                metric.title,
                metric.prometheus_type(
                    metric.title, metric.description, labelnames=metric.labels
                    )
            )
            