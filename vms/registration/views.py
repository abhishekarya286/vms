# third party

# Django
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.generic import TemplateView

# local Django
from administrator.forms import AdministratorForm
from administrator.models import Administrator
from organization.models import Organization
from organization.services import (create_organization, get_organizations_ordered_by_name,
                                   get_organization_by_id)
from registration.forms import UserForm
from registration.phone_validate import validate_phone
from registration.utils import volunteer_denied, match_password
from registration.tokens import account_activation_token
from volunteer.forms import VolunteerForm
from volunteer.validation import validate_file

class AdministratorSignupView(TemplateView):
    """
    Administrator and Volunteer signup is implemented as a TemplateView that
    displays the signup form.
    This method is responsible for displaying the register user view.
    Register Admin or volunteer is judged on the basis of users
    access rights.
    Only if user is registered and logged in and registered as an
    admin user, he/she is allowed to register others as an admin user.
    """
    registered = False
    organization_list = get_organizations_ordered_by_name()
    phone_error = False
    match_error = False

    @method_decorator(volunteer_denied)
    def dispatch(self, *args, **kwargs):
        return super(AdministratorSignupView, self).dispatch(*args, **kwargs)

    def get(self, request):
        user_form = UserForm(prefix="usr")
        administrator_form = AdministratorForm(prefix="admin")
        return render(
            request, 'registration/signup_administrator.html', {
                'user_form': user_form,
                'administrator_form': administrator_form,
                'registered': self.registered,
                'phone_error': self.phone_error,
                'match_error': self.match_error,
                'organization_list': self.organization_list,
            })

    def post(self, request):
        organization_list = get_organizations_ordered_by_name()
        if organization_list:
            if request.method == 'POST':
                user_form = UserForm(request.POST, prefix="usr")
                administrator_form = AdministratorForm(
                    request.POST, prefix="admin")

                if user_form.is_valid() and administrator_form.is_valid():
                    password1 = request.POST.get('usr-password')
                    password2 = request.POST.get('usr-confirm_password')
                    if not match_password(password1, password2):
                        self.match_error = True
                        return render(
                            request, 'registration/signup_administrator.html',
                            {
                                'user_form': user_form,
                                'administrator_form': administrator_form,
                                'registered': self.registered,
                                'phone_error': self.phone_error,
                                'match_error': self.match_error,
                                'organization_list': self.organization_list,
                            })
                    ad_country = request.POST.get('admin-country')
                    ad_phone = request.POST.get('admin-phone_number')

                    if ad_country and ad_phone:
                        if not validate_phone(ad_country, ad_phone):
                            self.phone_error = True
                            return render(
                                request,
                                'registration/signup_administrator.html', {
                                    'user_form': user_form,
                                    'administrator_form': administrator_form,
                                    'registered': self.registered,
                                    'phone_error': self.phone_error,
                                    'match_error': self.match_error,
                                    'organization_list':
                                    self.organization_list,
                                })

                    user = user_form.save()
                    user.set_password(user.password)
                    user.save()

                    administrator = administrator_form.save(commit=False)
                    administrator.user = user

                    # if organization isn't chosen from dropdown,
                    # the organization_id will be 0
                    organization_id = request.POST.get('organization_name')
                    organization = get_organization_by_id(organization_id)

                    if organization:
                        administrator.organization = organization
                    else:
                        unlisted_org = request.POST.get('admin-unlisted_organization')
                        org = create_organization(unlisted_org)
                        administrator.organization = org

                    administrator.save()
                    registered = True
                    messages.success(request,
                                     'You have successfully registered!')
                    return HttpResponseRedirect(reverse('home:index'))
                else:
                    return render(
                        request, 'registration/signup_administrator.html', {
                            'user_form': user_form,
                            'administrator_form': administrator_form,
                            'registered': self.registered,
                            'phone_error': self.phone_error,
                            'match_error': self.match_error,
                            'organization_list': self.organization_list,
                        })
        else:
            return render(request, 'home/home.html', {'error': True})


class VolunteerSignupView(TemplateView):
    registered = False
    organization_list = get_organizations_ordered_by_name()
    phone_error = False
    match_error = False

    def get(self, request):
        user_form = UserForm(prefix="usr")
        volunteer_form = VolunteerForm(prefix="vol")
        return render(
            request, 'registration/signup_volunteer.html', {
                'user_form': user_form,
                'volunteer_form': volunteer_form,
                'registered': self.registered,
                'phone_error': self.phone_error,
                'match_error': self.match_error,
                'organization_list': self.organization_list,
            })

    def post(self, request):
        organization_list = get_organizations_ordered_by_name()
        if organization_list:
            if request.method == 'POST':
                user_form = UserForm(request.POST, prefix="usr")
                volunteer_form = VolunteerForm(
                    request.POST, request.FILES, prefix="vol")

                if user_form.is_valid() and volunteer_form.is_valid():
                    password1 = request.POST.get('usr-password')
                    password2 = request.POST.get('usr-confirm_password')
                    if not match_password(password1, password2):
                        self.match_error = True
                        return render(
                            request, 'registration/signup_volunteer.html', {
                                'user_form': user_form,
                                'volunteer_form': volunteer_form,
                                'registered': self.registered,
                                'phone_error': self.phone_error,
                                'match_error': self.match_error,
                                'organization_list': self.organization_list,
                            })

                    vol_country = request.POST.get('vol-country')
                    vol_phone = request.POST.get('vol-phone_number')
                    if (vol_country and vol_phone):
                        if not validate_phone(vol_country, vol_phone):
                            self.phone_error = True
                            return render(
                                request, 'registration/signup_volunteer.html',
                                {
                                    'user_form': user_form,
                                    'volunteer_form': volunteer_form,
                                    'registered': self.registered,
                                    'phone_error': self.phone_error,
                                    'organization_list':
                                    self.organization_list,
                                })

                    if 'resume_file' in request.FILES:
                        my_file = volunteer_form.cleaned_data['resume_file']
                        if not validate_file(my_file):
                            return render(
                                request, 'registration/signup_volunteer.html',
                                {
                                    'user_form': user_form,
                                    'volunteer_form': volunteer_form,
                                    'registered': self.registered,
                                    'phone_error': self.phone_error,
                                    'organization_list':
                                    self.organization_list,
                                })

                    user = user_form.save()

                    user.set_password(user.password)
                    user.save()

                    volunteer = volunteer_form.save(commit=False)
                    volunteer.user = user

                    # if an organization isn't chosen from the dropdown,
                    # then organization_id will be 0
                    organization_id = request.POST.get('organization_name')
                    organization = get_organization_by_id(organization_id)

                    if organization:
                        volunteer.organization = organization
                    else:
                        unlisted_org = request.POST.get('vol-unlisted_organization')
                        org = Organization.objects.create(name=unlisted_org, approved_status=False)
                        org.save()
                        volunteer.organization = org

                    volunteer.reminder_days = 1
                    volunteer.save()
                    current_site = get_current_site(request)
                    mail_subject = 'Activate your account.'
                    message = render_to_string(
                        'registration/acc_active_email.html', {
                            'user': user,
                            'domain': current_site.domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': account_activation_token.make_token(user),
                        })
                    to_email = volunteer_form.cleaned_data.get('email')
                    email = EmailMessage(mail_subject, message, to=[to_email])
                    email.send()
                    return render(request, 'home/email_ask_confirm.html')
                else:
                    return render(
                        request, 'registration/signup_volunteer.html', {
                            'user_form': user_form,
                            'volunteer_form': volunteer_form,
                            'registered': self.registered,
                            'phone_error': self.phone_error,
                            'organization_list': self.organization_list,
                        })
        else:
            return render(request, 'home/home.html', {'error': True})


def activate(request, uidb64, token):
    """
    Checks token, if valid, then user will active and login

    :param uidb64: used to generate uid
    :param token: to be passed in request
    :return: email
    :raise: BadRequest
    """
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'home/confirmed_email.html')
    else:
        return HttpResponseBadRequest('Activation link is invalid!')

