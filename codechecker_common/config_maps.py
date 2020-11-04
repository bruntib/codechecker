# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
There are some config JSON files which contain some mapping between checkers
and some other property like severity, profile or guideline. This module
provides some mapping structures.
"""


from collections.abc import Mapping

from codechecker_common.util import load_json_or_empty


class SeverityMap(Mapping):
    """
    A dictionary which maps checker names to severity levels.
    If a key is not found in the map then it will return MEDIUM severity in
    case of compiler warnings and CRITICAL in case of compiler errors.
    """

    def __init__(self, *args, **kwargs):
        self.store = dict(*args, **kwargs)

    def __getitem__(self, key):
        # Key is not specified in the store and it is a compiler warning
        # or error.
        if key not in self.store:
            if key == 'clang-diagnostic-error':
                return "CRITICAL"
            elif key.startswith('clang-diagnostic-'):
                return "MEDIUM"

        return self.store.get(key, 'UNSPECIFIED')

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)


class ProfileMap(Mapping):
    """
    A dictionary which maps checker names and checker groups to profile names.
    A checker or checker group may be the member of multiple profiles.
    """
    def __init__(self, profile_map_file):
        self.store = load_json_or_empty(profile_map_file, {})
        self.__check_json_format(profile_map_file)

    def __check_json_format(self, profile_map_file):
        """
        This function checks the format of the given profile map config file.
        If this file doesn't meet the requirements, then CodeChecker exits with
        status 1.

        {
          "available_profiles": {
            "profile1": "description1",
            "profile2": "description2"
          },
          "analyzers": {
            "analyzer1": {
              "profile1": ['checker1', 'checker2']
            },
            "analyzer2": {
              "profile1": ['checker3'],
              "profile2": ['checker3', 'checker4']
            }
          }
        }
        """
        if 'available_profiles' not in self.store:
            raise ValueError(f'Format error in {profile_map_file}: '
                             '"available_profiles" key not found')
        if 'analyzers' not in self.store:
            raise ValueError(f'Format error in {profile_map_file}: '
                             '"analyzers" key not found')

        for analyzer, profiles in self.store['analyzers'].items():
            if not isinstance(profiles, dict):
                raise ValueError(f'Format error in {profile_map_file}: '
                                 f'value of {analyzer} must be a dictionary')

            diff = set(profiles) - set(self.store['available_profiles'])
            if diff:
                raise ValueError(f'Format error in {profile_map_file}: '
                                 f'{", ".join(diff)} at {analyzer} not '
                                 'documented under "available_profiles"')

            for profile, checkers in profiles.items():
                if not isinstance(checkers, list):
                    raise ValueError(f'Format error in {profile_map_file}: '
                                     f'value of {profile} at analyzer '
                                     f'{analyzer} must be a list')

    def __getitem__(self, key):
        """
        Returns the list of profiles to which the given checker name or group
        belongs.
        """
        result = []
        for profiles in self.store['analyzers'].values():
            for profile, checkers in profiles.items():
                if any(key.startswith(checker) for checker in checkers):
                    result.append(profile)
        return result

    def __iter__(self):
        """
        This mapping class maps checker groups/names to profiles. However,
        since not every checkers are listed necessarily in the profile config
        file, we can't iterate over them. Still, we map checkers to profiles
        and not in reverse, because we want to be consistent with the other
        mapping classes.
        """
        raise NotImplementedError("Can't iterate profiles by checkers.")

    def __len__(self):
        """
        Not implemented for the same reason as __iter__() is not implemented.
        """
        raise NotImplementedError("Can't determine the number of checkers")

    def by_profile(self, profile, analyzer_tool=None):
        """
        Return checkers of a given profile. Optionally an analyzer tool name
        can be given.
        """
        result = []
        for analyzer, profiles in self.store['analyzers'].items():
            if analyzer_tool is None or analyzer == analyzer_tool:
                result.extend(profiles.get(profile, []))
        return result

    def available_profiles(self):
        """
        Returns the dict of available profiles and their descriptions. The
        config file may contain profile groups of several analyzers. It is
        possible that some analyzer doesn't contain checkers of a specific
        profile.
        """
        return self.store['available_profiles']


class GuidelineMap(Mapping):
    def __init__(self, guideline_map_file):
        self.store = load_json_or_empty(guideline_map_file, {})
        self.__check_json_format(guideline_map_file)

    def __check_json_format(self, guideline_map_file):
        """
        This function checks the format of checker_guideline_map.json config
        file. If this config file doesn't meet the requirements, then
        CodeChecker exits with status 1.

        {
          "guidelines": {
            "guideline_1": "url_1",
            "guideline_2": "url_2"
          },
          "mapping": {
            "checker_1": {
              "guideline_1": ["id_1", "id_2"]
            }
          }
        }

        "guidelines" and "mapping" attributes are mandatory, the list of IDs
        must be a list, and the guideline name must be enumerated at
        "guidelines" attribute
        """
        if 'guidelines' not in self.store:
            raise ValueError(f'Format error in {guideline_map_file}: '
                             '"guideline" key not found')
        if 'mapping' not in self.store:
            raise ValueError(f'Format error in {guideline_map_file}: '
                             '"mapping" key not found')

        for checker, guidelines in self.store['mapping'].items():
            if not isinstance(guidelines, dict):
                raise ValueError(f'Format error in {guideline_map_file}: '
                                 f'value of {checker} must be a dictionary')

            diff = set(guidelines) - set(self.store['guidelines'])
            if diff:
                raise ValueError(f'Format error in {guideline_map_file}: '
                                 f'{", ".join(diff)} at {checker} not '
                                 'documented under "guidelines"')

            for guideline, ids in guidelines.items():
                if not isinstance(ids, list):
                    raise ValueError(f'Format error in {guideline_map_file}: '
                                     f'value of {guideline} at checker '
                                     f'{checker} must be a list')

    def __getitem__(self, key):
        return self.store['mapping'][key]

    def __iter__(self):
        return iter(self.store['mapping'])

    def __len__(self):
        return len(self.store)

    def by_guideline(self, guideline):
        """
        Return checkers belonging to a specific guideline. A checker belongs to
        a guideline if it reports on at least one guideline rule.
        """
        result = []
        for checker, guidelines in self.store['mapping'].items():
            if guideline in guidelines and guidelines[guideline]:
                result.append(checker)
        return result

    def by_rule(self, rule):
        """
        Return checkers belonging to a specific guideline rule.
        """
        result = []
        for checker, guidelines in self.store['mapping'].items():
            if any(rule in rules for _, rules in guidelines.items()):
                result.append(checker)
        return result

    def available_guidelines(self):
        """
        Returns the dict of available guidelines and their documentations'
        URLs.  It is possible that a guideline is not covered by any checkers.
        """
        return self.store['guidelines']
