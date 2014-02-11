# -*- coding: utf-8 -*-
DATABASES = {
    'default': {
        'ENGINE': 'crate.client.django.backend',
        'SERVERS': ['127.0.0.1:44209', ]
    },
    'other': {
        'ENGINE': 'crate.client.django.backend',
        'SERVERS': ['127.0.0.1:44209', ]
    }
}

SECRET_KEY = "0"*32

# Use a fast hasher to speed up tests.
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

INSTALLED_APPS = [
    "crate.client.django.tests"
]

TEST_RUNNER = 'django.test.runner.DiscoverRunner'
