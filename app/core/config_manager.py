"""
Singleton pattern - App configuration manager

Makes sure only one cofig manager instance exists for teh lifetime of the running app no matter where or how many times its constructed
"""

class ConfigManager:
    _instance = None

    def __new__(cls, *args, **keyword_args):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self):
        if self._initialised:
            return

        self._settings = {
            "app_name": "Enterprise Python Formative",
            "default_course_capacity": 30,
            "pass_mark": 50,
            "distinction_mark": 75,
        }

        self._initialised = True

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value):
        self._settings[key] = value

    def all_settings(self):
        return dict(self._settings)


    @classmethod
    def reset(cls):
        # clears singleton instance
        cls._instance = None

    def __repr__(self):
        return f"<ConfigManager id={id(self)}>"