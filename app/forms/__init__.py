from app.forms.auth_forms import LoginForm, RegisterForm, ChangePasswordForm
from app.forms.customer_forms import CustomerForm
from app.forms.lead_forms import LeadForm, ConvertLeadForm
from app.forms.opportunity_forms import OpportunityForm
from app.forms.followup_forms import FollowUpForm, RescheduleFollowUpForm
from app.forms.activity_forms import ActivityForm
from app.forms.user_forms import UserCreateForm, UserEditForm, AdminResetPasswordForm

__all__ = [
    'LoginForm', 'RegisterForm', 'ChangePasswordForm',
    'CustomerForm',
    'LeadForm', 'ConvertLeadForm',
    'OpportunityForm',
    'FollowUpForm', 'RescheduleFollowUpForm',
    'ActivityForm',
    'UserCreateForm', 'UserEditForm', 'AdminResetPasswordForm'
]

