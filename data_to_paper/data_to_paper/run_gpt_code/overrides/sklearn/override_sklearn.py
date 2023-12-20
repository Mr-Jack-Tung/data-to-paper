import functools
import inspect
from dataclasses import dataclass

from data_to_paper.run_gpt_code.overrides.attr_replacers import SystematicMethodReplacerContext

@dataclass
class SklearnOverride(SystematicMethodReplacerContext):
    obj_import_str: str = 'sklearn'

    @property
    def obj(self):
        # TODO: add more sklearn modules. Or fix generally. See comment in SystematicAttrReplacerContext.
        from sklearn import linear_model, svm  # noqa  Needed for the import to work inclusively.
        import sklearn
        return sklearn

    def _should_replace(self, parent, attr_name, attr) -> bool:
        return attr_name.startswith('fit')

    def _get_custom_wrapper(self, parent, attr_name, original_func):

        @functools.wraps(original_func)
        def wrapped(obj, *args, **kwargs):
            result = original_func(obj, *args, **kwargs)
            if self._is_called_from_data_to_paper():
                if hasattr(obj, '_prior_fit_results') and obj._prior_fit_results is result:
                    raise RuntimeWarning(
                        f"The `{original_func.__name__}` function was already called on this object. "
                        f"Multiple calls should be avoided as the same result instance is returned again.")
                obj._prior_fit_results = result

            return result

        return wrapped


@dataclass
class SklearnSearchLimitCheck(SystematicMethodReplacerContext):
    obj_import_str: str = 'sklearn.model_selection'
    max_iterations: int = 12  # Default max iterations limit

    def _should_replace(self, parent, attr_name, attr) -> bool:
        from sklearn.model_selection import ParameterGrid, ParameterSampler
        is_parameter_grid = issubclass(parent, ParameterGrid) and attr_name == "__len__"
        is_parameter_sampler = issubclass(parent, ParameterSampler) and attr_name == "__len__"
        return is_parameter_grid or is_parameter_sampler

    def _get_estimator_class_name(self):
        # Inspect the stack and find the class name of the estimator
        for frame_record in inspect.stack():
            if 'self' in frame_record.frame.f_locals:
                instance = frame_record.frame.f_locals['self']
                if hasattr(instance, 'fit'):
                    return instance.estimator.__class__.__name__
        return 'Unknown'

    def _get_custom_wrapper(self, parent, attr_name, original_func):

        @functools.wraps(original_func)
        def wrapped(obj, *args, **kwargs):
            original_len = original_func(obj, *args, **kwargs)
            if original_len > self.max_iterations:
                estimator_class_name = self._get_estimator_class_name()
                raise RuntimeWarning(f"The presumed total number of training iterations ({original_len}) for "
                                     f"{estimator_class_name} exceeds the maximum allowed iterations "
                                     f"({self.max_iterations}). \nNotice that the amount of iterations is a "
                                     f"multiplication of the numbers of possible values for each parameter when using "
                                     f"GridSearchCV or n_iter when using RandomizedSearchCV. \n"
                                     f"use only a subset of the parameters or reduce the number of iterations.")
            return original_len

        return wrapped

@dataclass
class SklearnRandomStateOverride(SystematicMethodReplacerContext):
    """
    This class overrides any provided sklearn class constructor (__init__) that supports random_state
    from sklearn to set random_state=0, ensuring reproducibility.
    """
    def _get_all_parents(self) -> list:
        from sklearn.ensemble import RandomForestRegressor # noqa  Needed for the import to work inclusively.
        from sklearn.linear_model import ElasticNet # noqa  Needed for the import to work inclusively.
        from sklearn.neural_network import MLPRegressor # noqa  Needed for the import to work inclusively.
        return [RandomForestRegressor, ElasticNet, MLPRegressor]

    def _should_replace(self, parent, attr_name, attr) -> bool:
        return attr_name == '__init__'

    def _get_custom_wrapper(self, parent, attr_name, original_func):

        @functools.wraps(original_func)
        def wrapped(obj, *args, **kwargs):
            # Set random_state=0 if not explicitly passed
            if 'random_state' not in kwargs:
                kwargs['random_state'] = 0

            # Call the original constructor
            return original_func(obj, *args, **kwargs)

        return wrapped


@dataclass
class SklearnNNSizeOverride(SystematicMethodReplacerContext):
    """
    This class overrides MLPRegressor and MLPClassifier to raise warning if the hidden_layer_sizes is too large.
    """
    max_layers: int = 2
    max_neurons_per_layer: int = 50

    def _get_all_parents(self) -> list:
        from sklearn.neural_network import MLPRegressor # noqa  Needed for the import to work inclusively.
        from sklearn.neural_network import MLPClassifier # noqa  Needed for the import to work inclusively.
        return [MLPRegressor, MLPClassifier]

    def _should_replace(self, parent, attr_name, attr) -> bool:
        return attr_name == '__init__'

    def _get_custom_wrapper(self, parent, attr_name, original_func):

        @functools.wraps(original_func)
        def wrapped(obj, *args, **kwargs):
            if 'hidden_layer_sizes' in kwargs:
                hidden_layer_sizes = kwargs['hidden_layer_sizes']
            else:
                # get the default hidden_layer_sizes
                hidden_layer_sizes = parent().hidden_layer_sizes
            if len(hidden_layer_sizes) > self.max_layers:
                raise RuntimeWarning(f"The given hidden_layer_sizes ({len(hidden_layer_sizes)}) is too large!\n"
                                     f"We only allow up to {self.max_layers} layers with {self.max_neurons_per_layer} "
                                     f"max neurons per layer.")
            for layer, layer_size in enumerate(hidden_layer_sizes):
                if layer_size > 50:
                    raise RuntimeWarning(f"The given hidden_layer_sizes, has a layer ({layer}) with too many neurons!\n"
                                         f"We only allow up to {self.max_layers} layers with "
                                         f"{self.max_neurons_per_layer} max neurons per layer.")

            # Call the original constructor
            return original_func(obj, *args, **kwargs)

        return wrapped
