#!/usr/bin/env python3
"""The engineering standard holds the judgment an agent applies to technical decisions when no human is asked:
platform-free principles, each with an observable sign, that linking docs extend but never override."""
import re
import unittest

import support

STANDARD = support.ROOT / 'standards/engineering.md'


def principles():
    section = STANDARD.read_text().split('## Principles', 1)[1].split('\n## ', 1)[0]
    return [' '.join(item.split()) for item in re.split(r'\n(?=- \*\*)', section) if item.strip().startswith('- **')]


class EngineeringStandard(unittest.TestCase):
    def test_every_principle_names_the_sign_that_shows_it_was_followed(self):
        found = principles()
        self.assertGreaterEqual(len(found), 12)
        for principle in found:
            self.assertRegex(principle, r'— shown by: \S', principle)

    def test_the_principles_cover_the_senior_engineer_traits_the_ticket_names(self):
        # The traits listed in ticket autopilot/01, from the research synthesis.
        traits = {'reversibility': r'one-way', 'proof on the real artifact': r'real artifact',
                  'feedback loop before theory': r'feedback loop', 'root causes': r'root cause',
                  'subtract before adding': r'[Ss]ubtract', 'idempotent operations': r'run twice\.\S* [^.]*(?<!never )converge when retried',
                  'the full objective': r'full objective', 'budgeting effort': r'[Bb]udget',
                  'encoding lessons in checks': r'repeated (mistake|correction)', 'independent review': r'[Ii]ndependent review',
                  'honest status': r'not run', "the user's experience": r'user'}
        titles = ' '.join(principles())
        for trait, pattern in traits.items():
            self.assertRegex(titles, pattern, trait)

    def test_it_applies_to_every_platform_alike(self):
        text = ' '.join(STANDARD.read_text().split())
        self.assertIn('mobile, web, backend, devops and SRE alike', text)
        self.assertIn('It names no platform, language or tool', text)
        # No single platform, language or tool may become the standard's scope.
        for word in ('iOS', 'Android', 'React', 'Kubernetes', 'AWS', 'Python', 'JavaScript', 'Swift', 'Docker', 'Terraform'):
            self.assertNotRegex(text, rf'\b{word}\b', word)

    def test_root_causes_are_searched_everywhere_but_fixed_within_scope(self):
        root = next(p for p in principles() if p.startswith('- **Fix the root cause'))
        self.assertIn('fix the instances in scope and report the rest as follow-ups', root)

    def test_docs_that_link_it_extend_it_and_never_override_it(self):
        text = ' '.join(STANDARD.read_text().split())
        self.assertIn('may add rules for their own decisions but never override or relax a principle', text)

    def test_it_links_the_standards_that_own_testing_design_and_docs_instead_of_restating_them(self):
        text = STANDARD.read_text()
        for owner in ('](tdd.md)', '](design.md)', '](documentation.md)'):
            self.assertIn(owner, text)
        self.assertNotIn('Red before green', text)

    def test_it_fits_one_read_beside_the_bootstrap(self):
        self.assertLess(len(STANDARD.read_bytes()), 6144)


if __name__ == '__main__':
    unittest.main()
