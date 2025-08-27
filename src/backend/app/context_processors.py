from .helper import get_counts_for_view


def global_variables(request):
    variables = {}

    # default

    # only for authenticated users
    # if request.user.is_authenticated:
    #     pass

    # only for superusers
    if request.user.is_superuser:
        variables["COUNTS"] = get_counts_for_view()

    return variables
