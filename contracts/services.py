from notifications.services import create_notification

def activate_contract(contract):
    contract.status = "active"
    contract.save()

    property = contract.property
    property.status = "occupied"
    property.save()

    tenant = contract.tenant
    tenant.property = property
    tenant.save()

    contract.generate_payments()

    # notifications
    create_notification(
        contract.tenant.user,
        "New Lease Created",
        f"Your lease for {property.title} is active"
    )