from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from contracts.models import Contract
from tenants.models import Tenant
from maintenance.models import MaintenanceRequest

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .services import create_notification





@receiver(post_save, sender=Contract)
def contract_created(sender, instance, created, **kwargs):
    if not created:
        return

    contract = instance

    # Tenant
    if contract.tenant and contract.tenant.user:
        create_notification(
            contract.tenant.user,
            "New Lease Created",
            f"You have a new lease for {contract.property.title}",
            type="contract"
        )

    # Agent
    if contract.agent:
        create_notification(
            contract.agent,
            "New Contract Assigned",
            f"Contract created for {contract.property.title}",
            type="contract"
        )

    # Landlord
    if contract.landlord:
        create_notification(
            contract.landlord,
            "Property Rented",
            f"{contract.property.title} is now occupied",
            type="contract"
        )
        
        
@receiver(post_delete, sender=Contract)
def contract_deleted(sender, instance, **kwargs):
    contract = instance

    if contract.tenant and contract.tenant.user:
        create_notification(
            contract.tenant.user,
            "Lease Terminated",
            f"Your lease for {contract.property.title} was ended",
            type="contract"
        )
        
@receiver(post_save, sender=Tenant)
def tenant_assigned(sender, instance, created, **kwargs):
    if not created:
        return

    tenant = instance

    if tenant.user:
        create_notification(
            tenant.user,
            "Tenant Profile Created",
            f"You were assigned to {tenant.property.title if tenant.property else 'a property'}",
            type="tenant"
        )
        
        
        
        
        
        
        
@receiver(post_save, sender=MaintenanceRequest)
def maintenance_created(sender, instance, created, **kwargs):
    if not created:
        return

    req = instance

    # Tenant
    if req.created_by:
        create_notification(
            req.created_by,
            "Maintenance Request Sent",
            f"Your request '{req.title}' was submitted",
            type="maintenance"
        )

    # Agent / landlord
    contract = req.contract

    if contract.agent:
        create_notification(
            contract.agent,
            "New Maintenance Request",
            req.title,
            type="maintenance"
        )

    if contract.landlord:
        create_notification(
            contract.landlord,
            "New Maintenance Request",
            req.title,
            type="maintenance"
        )
        
        
        
        
        
        
        
        
        
   