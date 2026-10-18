"""Test-only Django apps whose migrations put a database into the states that
PLT-2.12 to PLT-2.14 name. Their settings reuse Deskmate's configuration but
install only Deskmate's model-free root app and the synthetic apps, so production
apps' migrations cannot change the fixture plans or their fresh-database cases.
Their empty URL configuration also keeps Django's command checks from importing
the production apps' views and models.

None of these apps is in Deskmate's settings, and none is deployed.
"""

urlpatterns = []
