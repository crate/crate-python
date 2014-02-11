# -*- coding: utf-8 -*-
from crate.client.django.models.fields import *
from django.db.models import Model


class User(Model):
    id = IntegerField(primary_key=True)
    username = StringField()
    slogan = StringField(fulltext_index=True, analyzer="english")

    class Crate:
        number_of_replicas = 0
        number_of_shards = 4
        clustered_by = "id"
