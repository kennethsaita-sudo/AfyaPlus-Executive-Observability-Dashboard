from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer

# Without smoothing, sentence_bleu() computes a geometric mean over
# 1- through 4-gram precision. Short/varied clinical answers often
# have zero 4-gram overlap with the reference even when the content
# is correct, which collapses the geometric mean toward zero and
# shows up as near-zero floating point artifacts (e.g. 9e-156)
# instead of a clean, comparable 0.0-1.0 score. method4 (Chen &
# Cherry, 2014) smooths this out while still penalizing genuinely
# poor overlap, which is what you want for a report you can compare
# across models/features.
_smoothie = SmoothingFunction().method4


def bleu_score(reference, prediction):
    return sentence_bleu(
        [reference.split()],
        prediction.split(),
        smoothing_function=_smoothie
    )


def rouge_l(reference, prediction):

    scorer = rouge_scorer.RougeScorer(
        ['rougeL'],
        use_stemmer=True
    )

    return scorer.score(
        reference,
        prediction
    )['rougeL'].fmeasure


def token_f1(reference, prediction):

    ref_tokens = set(reference.lower().split())
    pred_tokens = set(prediction.lower().split())

    common = ref_tokens & pred_tokens

    if len(common) == 0:
        return 0

    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(ref_tokens)

    return 2 * precision * recall / (precision + recall)