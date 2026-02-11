from ._utils import variadic


def cli_option(params, command_option, param, separator=None):
    param = params.get(param)
    return ([] if param is None
            else [command_option, str(param)] if separator is None
            else [f'{command_option}{separator}{param}'])


def cli_bool_option(params, command_option, param, true_value='true', false_value='false', separator=None):
    param = params.get(param)
    assert param in (True, False, None)
    return cli_option({True: true_value, False: false_value}, command_option, param, separator)


def cli_valueless_option(params, command_option, param, expected_value=True):
    return [command_option] if params.get(param) == expected_value else []


def cli_configuration_args(argdict, keys, default=[], use_compat=True):
    if isinstance(argdict, (list, tuple)):  # for backward compatibility
        if use_compat:
            return argdict
        else:
            argdict = None
    if argdict is None:
        return default
    assert isinstance(argdict, dict)

    assert isinstance(keys, (list, tuple))
    for key_list in keys:
        arg_list = list(filter(
            lambda x: x is not None,
            [argdict.get(key.lower()) for key in variadic(key_list)]))
        if arg_list:
            return [arg for args in arg_list for arg in args]
    return default


def _configuration_args(main_key, argdict, exe, keys=None, default=[], use_compat=True):
    main_key, exe = main_key.lower(), exe.lower()
    root_key = exe if main_key == exe else f'{main_key}+{exe}'
    keys = [f'{root_key}{k}' for k in (keys or [''])]
    if root_key in keys:
        if main_key != exe:
            keys.append((main_key, exe))
        keys.append('default')
    else:
        use_compat = False
    return cli_configuration_args(argdict, keys, default, use_compat)
