"""
Management command to seed demo data for the Docker development environment.

Creates tenants, SSO providers, and test users for OIDC, SAML, and no-SSO flows.
"""

import uuid
import xml.etree.ElementTree as ET

import requests
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from django_allauth_multitenant_sso.models import SSOProvider, Tenant, TenantUser

User = get_user_model()

# Deterministic UUIDs for tenants (must match Keycloak realm SAML config)
ACME_TENANT_UUID = uuid.UUID("019400aa-aaaa-7aaa-aaaa-aaaaaaaaaaaa")
GLOBEX_TENANT_UUID = uuid.UUID("019400bb-bbbb-7bbb-bbbb-bbbbbbbbbbbb")
INITECH_TENANT_UUID = uuid.UUID("019400cc-cccc-7ccc-cccc-cccccccccccc")


class Command(BaseCommand):
    help = "Seed demo data for the Docker development environment"

    def add_arguments(self, parser):
        parser.add_argument(
            "--keycloak-url",
            default="http://keycloak:8080",
            help="Keycloak internal URL (default: http://keycloak:8080)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo data before seeding",
        )
        parser.add_argument(
            "--skip-keycloak",
            action="store_true",
            help="Skip Keycloak-dependent setup (OIDC/SAML providers)",
        )

    def handle(self, *args, **options):
        keycloak_url = options["keycloak_url"]
        reset = options["reset"]
        skip_keycloak = options["skip_keycloak"]

        if reset:
            self.stdout.write("Resetting demo data...")
            self._reset_data()

        self.stdout.write("Seeding demo data...")

        # 1. Create superuser
        self._create_superuser()

        # 2. Create tenants
        acme = self._create_tenant("Acme Corp", "acme-oidc", ACME_TENANT_UUID)
        globex = self._create_tenant("Globex Corp", "globex-saml", GLOBEX_TENANT_UUID)
        initech = self._create_tenant("Initech", "initech", INITECH_TENANT_UUID)

        # 3. Create SSO providers
        if not skip_keycloak:
            self._create_oidc_provider(acme, keycloak_url)
            self._create_saml_provider(globex, keycloak_url)
        else:
            self.stdout.write("  Skipping Keycloak-dependent SSO providers")

        # 4. Create test users and memberships
        admin_user = User.objects.get(email="admin@demo.com")
        self._create_membership(admin_user, acme, "owner")
        self._create_membership(admin_user, globex, "owner")
        self._create_membership(admin_user, initech, "owner")

        # Create tenant-specific test users
        alice = self._create_user("alice@acme.com", "password", "Alice", "Anderson")
        bob = self._create_user("bob@acme.com", "password", "Bob", "Baker")
        self._create_membership(alice, acme, "member")
        self._create_membership(bob, acme, "member")

        carol = self._create_user("carol@globex.com", "password", "Carol", "Chen")
        dave = self._create_user("dave@globex.com", "password", "Dave", "Davis")
        self._create_membership(carol, globex, "member")
        self._create_membership(dave, globex, "member")

        nouser = self._create_user("nouser@initech.com", "password", "No", "SSO")
        self._create_membership(nouser, initech, "member")

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully!"))

    def _reset_data(self):
        """Delete demo tenants and users."""
        slugs = ["acme-oidc", "globex-saml", "initech"]
        Tenant.objects.filter(slug__in=slugs).delete()
        emails = [
            "admin@demo.com",
            "alice@acme.com",
            "bob@acme.com",
            "carol@globex.com",
            "dave@globex.com",
            "nouser@initech.com",
        ]
        User.objects.filter(email__in=emails).delete()
        self.stdout.write("  Existing demo data deleted")

    def _create_superuser(self):
        """Create the demo admin superuser."""
        user, created = User.objects.get_or_create(
            email="admin@demo.com",
            defaults={
                "username": "admin",
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Admin",
                "last_name": "Demo",
            },
        )
        if created:
            user.set_password("demo")
            user.save()
            self.stdout.write("  Created superuser: admin@demo.com / demo")
        else:
            self.stdout.write("  Superuser admin@demo.com already exists")

    def _create_tenant(self, name, slug, tenant_uuid):
        """Create a tenant with a deterministic UUID."""
        tenant, created = Tenant.objects.get_or_create(
            slug=slug,
            defaults={
                "id": tenant_uuid,
                "name": name,
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(f"  Created tenant: {name} ({slug})")
        else:
            self.stdout.write(f"  Tenant {name} already exists")
        return tenant

    def _create_user(self, email, password, first_name, last_name):
        """Create a test user."""
        # Use email prefix as username (Django's default User model requires it)
        username = email.split("@")[0]
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
            },
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(f"  Created user: {email}")
        else:
            self.stdout.write(f"  User {email} already exists")
        return user

    def _create_membership(self, user, tenant, role):
        """Create a tenant membership."""
        _, created = TenantUser.objects.get_or_create(
            user=user,
            tenant=tenant,
            defaults={"role": role},
        )
        if created:
            self.stdout.write(f"  Added {user.email} to {tenant.name} as {role}")

    def _create_oidc_provider(self, tenant, keycloak_url):
        """Create OIDC SSO provider for Acme tenant."""
        # Manual endpoint configuration:
        # - Authorization endpoint uses localhost:8443 (browser redirect)
        # - Token/userinfo/jwks use keycloak:8080 (container-internal)
        provider, created = SSOProvider.objects.get_or_create(
            tenant=tenant,
            protocol="oidc",
            defaults={
                "name": "Keycloak OIDC",
                "is_active": True,
                "oidc_client_id": "django-multitenant-sso",
                "oidc_client_secret": "acme-oidc-client-secret",
                # Leave oidc_issuer empty to use manual endpoints
                "oidc_authorization_endpoint": "http://localhost:8443/realms/acme-oidc/protocol/openid-connect/auth",
                "oidc_token_endpoint": f"{keycloak_url}/realms/acme-oidc/protocol/openid-connect/token",
                "oidc_userinfo_endpoint": f"{keycloak_url}/realms/acme-oidc/protocol/openid-connect/userinfo",
                "oidc_jwks_uri": f"{keycloak_url}/realms/acme-oidc/protocol/openid-connect/certs",
                "oidc_scopes": "openid email profile",
            },
        )
        if created:
            # Enable SSO on the tenant
            tenant.sso_enabled = True
            tenant.save()
            self.stdout.write("  Created OIDC provider for Acme Corp")
        else:
            self.stdout.write("  OIDC provider for Acme Corp already exists")

    def _create_saml_provider(self, tenant, keycloak_url):
        """Create SAML SSO provider for Globex tenant."""
        # Fetch the IdP signing certificate from Keycloak's SAML descriptor
        x509_cert = self._fetch_saml_certificate(keycloak_url)
        if not x509_cert:
            self.stdout.write(
                self.style.WARNING(
                    "  Could not fetch SAML certificate from Keycloak. "
                    "SAML provider created without certificate."
                )
            )

        provider, created = SSOProvider.objects.get_or_create(
            tenant=tenant,
            protocol="saml",
            defaults={
                "name": "Keycloak SAML",
                "is_active": True,
                "saml_entity_id": f"http://localhost:8443/realms/globex-saml",
                "saml_sso_url": "http://localhost:8443/realms/globex-saml/protocol/saml",
                "saml_x509_cert": x509_cert or "",
                "saml_attribute_mapping": {
                    "email": "email",
                    "first_name": "firstName",
                    "last_name": "lastName",
                },
            },
        )
        if created:
            tenant.sso_enabled = True
            tenant.save()
            self.stdout.write("  Created SAML provider for Globex Corp")
        else:
            # Update certificate if it was empty and we now have one
            if x509_cert and not provider.saml_x509_cert:
                provider.saml_x509_cert = x509_cert
                provider.save()
                self.stdout.write("  Updated SAML certificate for Globex Corp")
            else:
                self.stdout.write("  SAML provider for Globex Corp already exists")

    def _fetch_saml_certificate(self, keycloak_url):
        """Fetch the SAML signing certificate from Keycloak's descriptor endpoint."""
        descriptor_url = (
            f"{keycloak_url}/realms/globex-saml/protocol/saml/descriptor"
        )
        self.stdout.write(f"  Fetching SAML certificate from {descriptor_url}...")

        try:
            response = requests.get(descriptor_url, timeout=30)
            response.raise_for_status()

            # Parse the XML to extract the X.509 certificate
            root = ET.fromstring(response.text)
            # Namespace map for SAML metadata XML
            ns = {
                "md": "urn:oasis:names:tc:SAML:2.0:metadata",
                "ds": "http://www.w3.org/2000/09/xmldsig#",
            }
            # Find the signing certificate
            for key_descriptor in root.findall(".//md:KeyDescriptor", ns):
                use = key_descriptor.get("use", "signing")
                if use == "signing":
                    cert_elem = key_descriptor.find(".//ds:X509Certificate", ns)
                    if cert_elem is not None and cert_elem.text:
                        cert = cert_elem.text.strip()
                        self.stdout.write("  SAML certificate fetched successfully")
                        return cert

            # If no signing-specific key, try any certificate
            cert_elem = root.find(".//ds:X509Certificate", ns)
            if cert_elem is not None and cert_elem.text:
                cert = cert_elem.text.strip()
                self.stdout.write("  SAML certificate fetched successfully")
                return cert

            self.stdout.write(
                self.style.WARNING("  No certificate found in SAML descriptor")
            )
            return None
        except requests.exceptions.ConnectionError:
            self.stdout.write(
                self.style.WARNING(
                    f"  Could not connect to Keycloak at {keycloak_url}"
                )
            )
            return None
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"  Error fetching SAML certificate: {e}")
            )
            return None
