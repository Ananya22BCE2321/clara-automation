import unittest

from models import AccountMemo
from patcher import apply_patch


class TestPatcher(unittest.TestCase):
    def test_apply_patch_idempotent(self):
        v1 = AccountMemo(account_id="t1", business_name="X", contact_name=None, contact_number=None, timezone=None, business_hours={'example': 'from 9am to 5pm'}, notes=None)
        updates = {'timezone': 'UTC', 'business_hours': {'example': 'from 9am to 5pm'}}

        v2, changelog1 = apply_patch(v1, updates)
        # first run should report timezone change
        self.assertTrue(len(changelog1.entries) >= 1)

        # applying the same updates to the already-updated memo should yield no new entries
        v3, changelog2 = apply_patch(v2, updates)
        self.assertEqual(len(changelog2.entries), 0)


if __name__ == '__main__':
    unittest.main()
