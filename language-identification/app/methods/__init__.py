from .alphabet import AlphabetMethod
from .base import Method, Prediction
from .neural import NeuralMethod
from .short_words import ShortWordsMethod

METHOD_CLASSES = (ShortWordsMethod, AlphabetMethod, NeuralMethod)
METHOD_TITLES = {cls.key: cls.title for cls in METHOD_CLASSES}

__all__ = [
    "AlphabetMethod",
    "Method",
    "METHOD_CLASSES",
    "METHOD_TITLES",
    "NeuralMethod",
    "Prediction",
    "ShortWordsMethod",
]
