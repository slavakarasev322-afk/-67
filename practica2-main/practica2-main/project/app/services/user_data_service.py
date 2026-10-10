"""Ownership-enforcing wrappers for the existing meter service."""
from __future__ import annotations
from typing import Any

from app.services import meter_service
from app.services.account_service import (
    assert_meter_owned,
    assert_property_owned,
    create_property_for_user,
    list_properties_for_user,
)


def list_properties(user_id: int) -> list[dict[str, Any]]:
    return list_properties_for_user(user_id)


def create_property(address: str, user_id: int) -> int:
    return create_property_for_user(address, user_id)


def list_meters(property_id: int | None, user_id: int) -> list[dict[str, Any]]:
    if property_id is None:
        return []
    assert_property_owned(property_id, user_id)
    return meter_service.list_meters(int(property_id))


def list_readings(property_id: int | None, user_id: int) -> list[dict[str, Any]]:
    if property_id is None:
        return []
    assert_property_owned(property_id, user_id)
    return meter_service.list_readings(int(property_id))


def create_meter(
    meter_type: str,
    serial_number: str,
    verification_date: str,
    property_id: int,
    user_id: int,
) -> Any:
    assert_property_owned(property_id, user_id)
    return meter_service.create_meter(
        meter_type, serial_number, verification_date, int(property_id)
    )


def create_reading(meter_id: int, value: str | float, user_id: int) -> Any:
    assert_meter_owned(meter_id, user_id)
    return meter_service.create_reading(int(meter_id), str(value))


def remove_meter(meter_id: int, user_id: int) -> Any:
    assert_meter_owned(meter_id, user_id)
    return meter_service.remove_meter(int(meter_id))
