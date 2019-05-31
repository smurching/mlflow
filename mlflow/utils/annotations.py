from functools import wraps


def experimental(func):
    """
    Decorator for marking APIs experimental in the docstring.

    :param func: A function to mark
    :returns Decorated function.
    """
    notice = ".. Note:: Experimental: This method may change or " + \
             "be removed in a future release without warning.\n"
    func.__doc__ = notice + func.__doc__
    return func


def deprecated(alternative=None, since=None):
    """
    Decorator for marking APIs deprecated in the docstring.

    :param func: A function to mark
    :returns Decorated function.
    """
    def deprecated_func(func):
        since_str = " since %s" % since if since else ""
        notice = ".. Warning:: Deprecated%s: This method will be removed in " % since_str + \
                 "a near future release."
        if alternative is not None and alternative.strip():
            notice += " Use ``%s`` instead." % alternative
        func.__doc__ = notice + "\n" + func.__doc__
        return func
    return deprecated_func


def keyword_only(func):
    """
    A decorator that forces keyword arguments in the wrapped method.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if len(args) > 0:
            raise TypeError("Method %s only takes keyword arguments." % func.__name__)
        return func(**kwargs)
    notice = ".. Note:: This method requires all argument be specified by keyword.\n"
    wrapper.__doc__ = notice + wrapper.__doc__
    return wrapper
