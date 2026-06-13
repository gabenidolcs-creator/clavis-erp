from django.urls import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
)


@pytest.mark.django_db
def test_enable_sharing_sets_public_true(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)

    url = reverse("api:dashboard:share:enable", kwargs={"dashboard_id": dashboard.id})
    response = api_client.post(
        url,
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK
    response_json = response.json()
    assert response_json["public"] is True
    assert "slug" in response_json

    dashboard.refresh_from_db()
    assert dashboard.public is True


@pytest.mark.django_db
def test_disable_sharing_sets_public_false(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)
    dashboard.public = True
    dashboard.save()

    enable_url = reverse(
        "api:dashboard:share:disable", kwargs={"dashboard_id": dashboard.id}
    )
    response = api_client.post(
        enable_url,
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK
    response_json = response.json()
    assert response_json["public"] is False

    dashboard.refresh_from_db()
    assert dashboard.public is False

    # Subsequent GET to public endpoint returns 401
    public_url = reverse(
        "api:dashboard:share:public_dashboard",
        kwargs={"slug": dashboard.slug},
    )
    public_response = api_client.get(public_url)
    assert public_response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_rotate_slug_invalidates_old_slug(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)
    dashboard.public = True
    dashboard.save()
    old_slug = dashboard.slug

    rotate_url = reverse(
        "api:dashboard:share:rotate_slug", kwargs={"dashboard_id": dashboard.id}
    )
    response = api_client.post(
        rotate_url,
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK
    new_slug = response.json()["slug"]
    assert new_slug != old_slug

    # Old slug returns 401
    old_url = reverse(
        "api:dashboard:share:public_dashboard",
        kwargs={"slug": old_slug},
    )
    old_response = api_client.get(old_url)
    assert old_response.status_code == HTTP_401_UNAUTHORIZED

    # New slug returns 200
    new_url = reverse(
        "api:dashboard:share:public_dashboard",
        kwargs={"slug": new_slug},
    )
    new_response = api_client.get(new_url)
    assert new_response.status_code == HTTP_200_OK


@pytest.mark.django_db
def test_public_dashboard_requires_public_true(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)
    # public=False by default

    url = reverse(
        "api:dashboard:share:public_dashboard",
        kwargs={"slug": dashboard.slug},
    )
    response = api_client.get(url)

    # Must be 401, not 404 — no existence oracle
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_enable_sharing_requires_update_permission(api_client, data_fixture):
    # Create dashboard owned by a different user
    dashboard = data_fixture.create_dashboard_application()

    # This user is not in the workspace at all
    user, token = data_fixture.create_user_and_token()

    url = reverse("api:dashboard:share:enable", kwargs={"dashboard_id": dashboard.id})
    response = api_client.post(
        url,
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_public_dashboard_returns_dashboard_info(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user, name="Test Board")
    dashboard.public = True
    dashboard.save()

    url = reverse(
        "api:dashboard:share:public_dashboard",
        kwargs={"slug": dashboard.slug},
    )
    response = api_client.get(url)

    assert response.status_code == HTTP_200_OK
    response_json = response.json()
    assert response_json["id"] == dashboard.id
    assert response_json["name"] == "Test Board"
    assert "widgets" in response_json
    assert "data_sources" in response_json


@pytest.mark.django_db
def test_public_dispatch_requires_public_true(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)
    # public=False by default — dispatch must not leak existence
    widget = data_fixture.create_summary_widget(dashboard=dashboard)
    data_source = widget.data_source

    url = reverse(
        "api:dashboard:share:public_dispatch",
        kwargs={"slug": dashboard.slug, "data_source_id": data_source.id},
    )
    response = api_client.get(url)

    # Must be 401, not 404 — no existence oracle
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_public_dispatch_unconfigured_returns_400(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    dashboard = data_fixture.create_dashboard_application(user=user)
    dashboard.public = True
    dashboard.save()
    widget = data_fixture.create_summary_widget(dashboard=dashboard)
    data_source = widget.data_source

    url = reverse(
        "api:dashboard:share:public_dispatch",
        kwargs={"slug": dashboard.slug, "data_source_id": data_source.id},
    )
    # No auth header — public endpoint, AnonymousUser principal
    response = api_client.get(url)

    # Unconfigured data source → 400, not 401 (proves AnonymousUser was accepted)
    assert response.status_code == HTTP_400_BAD_REQUEST
