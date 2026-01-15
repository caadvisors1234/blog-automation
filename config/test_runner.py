from django.conf import settings
from django.test.runner import DiscoverRunner


class PatchedDiscoverRunner(DiscoverRunner):
    """
    Test runner that pins the top-level directory to BASE_DIR.
    This avoids module import conflicts for "tests" packages.
    """

    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        if test_labels is None:
            test_labels = ['.']

        suite = self.test_suite()
        discover_kwargs = {'top_level_dir': str(settings.BASE_DIR)}

        for label in test_labels:
            tests = self.load_tests_for_label(label, discover_kwargs)
            suite.addTests(tests)

        if extra_tests:
            suite.addTests(extra_tests)

        return suite
