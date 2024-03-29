# Copyright (C) 2012-2014 by the Free Software Foundation, Inc.
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

"""Configuration system interface."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ConfigurationUpdatedEvent',
    'IConfiguration',
    'MissingConfigurationFileError',
    ]


from zope.interface import Interface

from mailman.core.errors import MailmanError



class MissingConfigurationFileError(MailmanError):
    """A named configuration file was not found."""

    def __init__(self, path):
        self.path = path



class IConfiguration(Interface):
    """Marker interface; used for adaptation in the REST API."""



class ConfigurationUpdatedEvent:
    """The system-wide global configuration was updated."""
    def __init__(self, config):
        self.config = config
