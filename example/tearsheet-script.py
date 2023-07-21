import pandas
import typing

def get_template_values(
    df_returns: typing.Optional[pandas.Series],
    df_benchmark: typing.Optional[pandas.Series],
    df_dump: typing.Optional[pandas.DataFrame],
    df_metrics: typing.Optional[pandas.DataFrame],
    **kwargs
):
    apply, apply_re = {}, {}

    apply.update({
        "website": "direct value",
        "title": lambda _: "lazy" + "value",
    })

    return apply, apply_re
