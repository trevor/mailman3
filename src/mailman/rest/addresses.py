# Copyright (C) 2011-2014 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""REST for addresses."""

from __future__ import absolute_import, print_function,unicode_literals

__metaclass__ = type
__all__ = [
    'AllAddresses',
    'AnAddress',
    'UserAddresses',
    ]


from operator import attrgetter
from restish import http, resource
from zope.component import getUtility

from mailman.interfaces.address import (
    ExistingAddressError, InvalidEmailAddressError)
from mailman.interfaces.usermanager import IUserManager
from mailman.rest.helpers import CollectionMixin, etag, no_content, path_to
from mailman.rest.members import MemberCollection
from mailman.rest.preferences import Preferences
from mailman.rest.validator import Validator
from mailman.utilities.datetime import now



class _AddressBase(resource.Resource, CollectionMixin):
    """Shared base class for address representations."""

    def _resource_as_dict(self, address):
        """See `CollectionMixin`."""
        # The canonical url for an address is its lower-cased version,
        # although it can be looked up with either its original or lower-cased
        # email address.
        representation = dict(
            email=address.email,
            original_email=address.original_email,
            registered_on=address.registered_on,
            self_link=path_to('addresses/{0}'.format(address.email)),
            )
        # Add optional attributes.  These can be None or the empty string.
        if address.display_name:
            representation['display_name'] = address.display_name
        if address.verified_on:
            representation['verified_on'] = address.verified_on
        return representation

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(getUtility(IUserManager).addresses)



class AllAddresses(_AddressBase):
    """The addresses."""

    @resource.GET()
    def collection(self, request):
        """/addresses"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))



class _VerifyResource(resource.Resource):
    """A helper resource for verify/unverify POSTS."""

    def __init__(self, address, action):
        self._address = address
        self._action = action
        assert action in ('verify', 'unverify')

    @resource.POST()
    def verify(self, request):
        # We don't care about the POST data, just do the action.
        if self._action == 'verify' and self._address.verified_on is None:
            self._address.verified_on = now()
        elif self._action == 'unverify':
            self._address.verified_on = None
        return no_content()


class AnAddress(_AddressBase):
    """An address."""

    def __init__(self, email):
        """Get an address by either its original or lower-cased email.

        :param email: The email address of the `IAddress`.
        :type email: string
        """
        self._address = getUtility(IUserManager).get_address(email)

    @resource.GET()
    def address(self, request):
        """Return a single address."""
        if self._address is None:
            return http.not_found()
        return http.ok([], self._resource_as_json(self._address))

    @resource.child()
    def memberships(self, request, segments):
        """/addresses/<email>/memberships"""
        if len(segments) != 0:
            return http.bad_request()
        if self._address is None:
            return http.not_found()
        return AddressMemberships(self._address)

    @resource.child()
    def preferences(self, request, segments):
        """/addresses/<email>/preferences"""
        if len(segments) != 0:
            return http.bad_request()
        if self._address is None:
            return http.not_found()
        child = Preferences(
            self._address.preferences,
            'addresses/{0}'.format(self._address.email))
        return child, []

    @resource.child()
    def verify(self, request, segments):
        """/addresses/<email>/verify"""
        if len(segments) != 0:
            return http.bad_request()
        if self._address is None:
            return http.not_found()
        child = _VerifyResource(self._address, 'verify')
        return child, []

    @resource.child()
    def unverify(self, request, segments):
        """/addresses/<email>/verify"""
        if len(segments) != 0:
            return http.bad_request()
        if self._address is None:
            return http.not_found()
        child = _VerifyResource(self._address, 'unverify')
        return child, []



class UserAddresses(_AddressBase):
    """The addresses of a user."""

    def __init__(self, user):
        self._user = user
        super(UserAddresses, self).__init__()

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return sorted(self._user.addresses,
                      key=attrgetter('original_email'))

    @resource.GET()
    def collection(self, request):
        """/addresses"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))

    @resource.POST()
    def create(self, request):
        """POST to /addresses

        Add a new address to the user record.
        """
        if self._user is None:
            return http.not_found()
        user_manager = getUtility(IUserManager)
        validator = Validator(email=unicode,
                              display_name=unicode,
                              _optional=('display_name',))
        try:
            address = user_manager.create_address(**validator(request))
        except ValueError as error:
            return http.bad_request([], str(error))
        except InvalidEmailAddressError:
            return http.bad_request([], b'Invalid email address')
        except ExistingAddressError:
            return http.bad_request([], b'Address already exists')
        else:
            # Link the address to the current user and return it.
            address.user = self._user
            location = path_to('addresses/{0}'.format(address.email))
            return http.created(location, [], None)



def membership_key(member):
    # Sort first by mailing list, then by address, then by role.
    return member.list_id, member.address.email, member.role.value


class AddressMemberships(MemberCollection):
    """All the memberships of a particular email address."""

    def __init__(self, address):
        super(AddressMemberships, self).__init__()
        self._address = address

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        # XXX Improve this by implementing a .memberships attribute on
        # IAddress, similar to the way IUser does it.
        #
        # Start by getting the IUser that controls this address.  For now, if
        # the address is not controlled by a user, return the empty set.
        # Later when we address the XXX comment, it will return some
        # memberships.  But really, it should not be legal to subscribe an
        # address to a mailing list that isn't controlled by a user -- maybe!
        user = getUtility(IUserManager).get_user(self._address.email)
        if user is None:
            return []
        return sorted((member for member in user.memberships.members
                       if member.address == self._address),
                      key=membership_key)
