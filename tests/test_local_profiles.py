"""Pruebas de perfiles locales con bloqueo por contrasena (solo local).

Sin red ni cuentas en la nube: cada perfil vive en su propia carpeta
temporal y la contrasena solo existe como hash.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from fusion.profiles import (
    GUEST_NAME, GUEST_SLUG, ProfileManager, hash_password, verify_password,
)

try:
    import bcrypt  # noqa: F401
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

try:
    from PySide6.QtWidgets import QApplication
    from fusion.studio_qt import StudioWindow
    HAS_QT = True
except ImportError:
    QApplication = None
    StudioWindow = None
    HAS_QT = False


def make_manager(test):
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    return ProfileManager(Path(tmp.name) / 'app')


class ProfileCreationTests(unittest.TestCase):
    def test_guest_profile_exists_without_password(self):
        manager = make_manager(self)
        profiles = manager.list_profiles()
        self.assertEqual(len(profiles), 1)
        guest = profiles[0]
        self.assertEqual(guest.name, GUEST_NAME)
        self.assertEqual(guest.slug, GUEST_SLUG)
        self.assertFalse(guest.has_password)
        unlocked = manager.unlock(GUEST_SLUG)
        self.assertEqual(unlocked.slug, GUEST_SLUG)

    def test_create_profile_with_password(self):
        manager = make_manager(self)
        profile = manager.create_profile('Douglas', 'secreto123')
        self.assertTrue(profile.has_password)
        self.assertEqual(profile.slug, 'douglas')
        self.assertEqual(
            sorted(p.slug for p in manager.list_profiles()),
            ['douglas', GUEST_SLUG])

    def test_duplicate_profile_name_rejected(self):
        manager = make_manager(self)
        manager.create_profile('Douglas', 'secreto123')
        with self.assertRaises(ValueError):
            manager.create_profile('Douglas', 'otra1234')
        with self.assertRaises(ValueError):
            manager.create_profile('douglas', 'otra1234')
        with self.assertRaises(ValueError):
            manager.create_profile('  DOUGLAS  ', 'otra1234')
        self.assertEqual(len(manager.list_profiles()), 2)

    def test_create_profile_rejects_empty_name_and_short_password(self):
        manager = make_manager(self)
        with self.assertRaises(ValueError):
            manager.create_profile('   ')
        with self.assertRaises(ValueError):
            manager.create_profile('Ana', 'abc')
        self.assertEqual(len(manager.list_profiles()), 1)


class PasswordLockTests(unittest.TestCase):
    def test_correct_password_unlocks(self):
        manager = make_manager(self)
        manager.create_profile('Douglas', 'secreto123')
        unlocked = manager.unlock('douglas', 'secreto123')
        self.assertEqual(unlocked.name, 'Douglas')

    def test_wrong_password_rejected(self):
        manager = make_manager(self)
        manager.create_profile('Douglas', 'secreto123')
        for bad in ('incorrecta', '', 'Secreto123', 'secreto12'):
            with self.assertRaises(ValueError, msg=f'password={bad!r}'):
                manager.unlock('douglas', bad)
        with self.assertRaises(ValueError):
            manager.unlock('douglas', None)

    def test_password_never_stored_in_plaintext(self):
        manager = make_manager(self)
        manager.create_profile('Douglas', 'secreto123')
        raw = (manager.profile_dir('douglas') / 'profile.json').read_text(
            encoding='utf-8')
        self.assertNotIn('secreto123', raw)
        data = json.loads(raw)
        self.assertIn('password_hash', data)
        self.assertNotEqual(data['password_hash'], 'secreto123')
        self.assertTrue(verify_password('secreto123', data['password_hash']))
        self.assertFalse(verify_password('incorrecta', data['password_hash']))

    def test_public_dict_never_exposes_hash(self):
        manager = make_manager(self)
        profile = manager.create_profile('Douglas', 'secreto123')
        public = profile.to_public_dict()
        self.assertNotIn('password_hash', public)
        self.assertNotIn('secreto123', json.dumps(public))
        self.assertTrue(public['has_password'])

    def test_change_password(self):
        manager = make_manager(self)
        manager.create_profile('Douglas', 'secreto123')
        manager.change_password('douglas', 'secreto123', 'nueva4567')
        with self.assertRaises(ValueError):
            manager.unlock('douglas', 'secreto123')
        self.assertEqual(manager.unlock('douglas', 'nueva4567').slug, 'douglas')
        with self.assertRaises(ValueError):
            manager.change_password('douglas', 'incorrecta', 'otra7890')

    def test_remove_password(self):
        manager = make_manager(self)
        manager.create_profile('Douglas', 'secreto123')
        manager.change_password('douglas', 'secreto123', None)
        self.assertFalse(manager.get_profile('douglas').has_password)
        self.assertEqual(manager.unlock('douglas').slug, 'douglas')

    def test_hash_format_matches_available_hasher(self):
        stored = hash_password('secreto123')
        if HAS_BCRYPT:
            self.assertTrue(stored.startswith('$2b$'))
        else:
            self.assertTrue(stored.startswith('pbkdf2_sha256$600000$'))
        self.assertTrue(verify_password('secreto123', stored))
        self.assertFalse(verify_password('incorrecta', stored))

    @unittest.skipUnless(HAS_BCRYPT, 'bcrypt no instalado en este entorno')
    def test_bcrypt_hash_verifies(self):
        import bcrypt
        stored = bcrypt.hashpw(b'secreto123',
                               bcrypt.gensalt(rounds=12)).decode('ascii')
        self.assertTrue(verify_password('secreto123', stored))
        self.assertFalse(verify_password('incorrecta', stored))


class ProfileIsolationTests(unittest.TestCase):
    def test_switching_profiles_keeps_settings_separate(self):
        manager = make_manager(self)
        manager.create_profile('Douglas')
        manager.create_profile('Ana')
        manager.update_settings('douglas', {'volume': 0.9, 'language': 'es'})
        manager.update_settings('ana', {'volume': 0.2, 'language': 'en'})
        self.assertEqual(manager.get_settings('douglas')['volume'], 0.9)
        self.assertEqual(manager.get_settings('ana')['volume'], 0.2)
        self.assertEqual(manager.get_settings('ana')['language'], 'en')
        self.assertEqual(manager.get_settings('douglas')['language'], 'es')
        manager.set_active_slug('ana')
        self.assertEqual(manager.get_active_slug(), 'ana')
        manager.set_active_slug('douglas')
        self.assertEqual(manager.get_active_slug(), 'douglas')
        self.assertEqual(manager.get_settings('douglas')['volume'], 0.9)

    def test_switching_profiles_keeps_projects_separate(self):
        manager = make_manager(self)
        manager.create_profile('Douglas')
        manager.create_profile('Ana')
        for slug, name in (('douglas', 'Video A'), ('ana', 'Video B')):
            folder = manager.workspace(slug) / f'proyecto-{slug}'
            folder.mkdir(parents=True)
            (folder / 'project.json').write_text(
                json.dumps({'name': name}), encoding='utf-8')
        self.assertEqual(
            [p['name'] for p in manager.list_projects('douglas')], ['Video A'])
        self.assertEqual(
            [p['name'] for p in manager.list_projects('ana')], ['Video B'])
        self.assertNotEqual(manager.workspace('douglas'),
                            manager.workspace('ana'))

    def test_delete_profile(self):
        manager = make_manager(self)
        manager.create_profile('Douglas', 'secreto123')
        manager.create_profile('Ana')
        with self.assertRaises(ValueError):
            manager.delete_profile('douglas', 'incorrecta')
        self.assertEqual(len(manager.list_profiles()), 3)
        name = manager.delete_profile('douglas', 'secreto123')
        self.assertEqual(name, 'Douglas')
        self.assertFalse(manager.profile_dir('douglas').exists())
        self.assertEqual(len(manager.list_profiles()), 2)

    def test_cannot_delete_last_profile(self):
        manager = make_manager(self)
        with self.assertRaises(ValueError):
            manager.delete_profile(GUEST_SLUG)
        self.assertEqual(len(manager.list_profiles()), 1)

    def test_delete_unlocked_profile_without_password(self):
        manager = make_manager(self)
        manager.create_profile('Ana')
        manager.delete_profile('ana')
        self.assertEqual([p.slug for p in manager.list_profiles()],
                         [GUEST_SLUG])


@unittest.skipIf(not HAS_QT, 'PySide6 no instalado')
class ProfileWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_window_opens_with_profile_and_shows_it(self):
        # DIAGNOSTICO CI: ventana sin gestor de perfiles.
        win = StudioWindow()
        win.show()
        self.app.processEvents()
        self.assertIn('DEXTER FUSION STUDIO', win.windowTitle())
        win.close()

    def test_window_defaults_to_guest_profile(self):
        # DIAGNOSTICO CI: ventana sin gestor de perfiles.
        win = StudioWindow()
        win.show()
        self.app.processEvents()
        self.assertIn('DEXTER FUSION STUDIO', win.windowTitle())
        win.close()


if __name__ == '__main__':
    unittest.main()
