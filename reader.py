#!/usr/bin/python
# -*- coding: utf8 -*-

import yaml
import glob
import io


def read_yaml_file(filename):
    with io.open(filename, 'r', encoding='utf-8') as stream:
        try:
            return(yaml.safe_load(stream))
        except yaml.YAMLError as exc:
            raise (exc)

