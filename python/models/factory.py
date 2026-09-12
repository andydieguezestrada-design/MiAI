from python.admin.provider_manager import ProviderManager


def _make(name: str):
    return ProviderManager.build_one(name)


def create_provider():
    return ProviderManager().build()
