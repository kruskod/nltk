import itertools

from nltk.topology.orderedSet import OrderedSet


def unique_permutations(seq):
    """
    Yield only unique permutations of seq in an efficient way.

    A python implementation of Knuth's "Algorithm L", also known from the
    std::next_permutation function of C++, and as the permutation algorithm
    of Narayana Pandita.
    """

    # Precalculate the indices we'll be iterating over for speed
    i_indices = range(len(seq) - 1, -1, -1)
    k_indices = i_indices[1:]

    # The algorithm specifies to start with a sorted version
    seq = sorted(seq)

    while True:
        yield seq

        # Working backwards from the last-but-one index,           k
        # we find the index of the first decrease in value.  0 0 1 0 1 1 1 0
        for k in k_indices:
            if seq[k] < seq[k + 1]:
                break
        else:
            # Introducing the slightly unknown python for-else syntax:
            # else is executed only if the break statement was never reached.
            # If this is the case, seq is weakly decreasing, and we're done.
            return

        # Get item from sequence only once, for speed
        k_val = seq[k]

        # Working backwards starting with the last item,           k     i
        # find the first one greater than the one at k       0 0 1 0 1 1 1 0
        for i in i_indices:
            if k_val < seq[i]:
                break

        # Swap them in the most efficient way
        (seq[k], seq[i]) = (seq[i], seq[k])                #       k     i
                                                           # 0 0 1 1 1 1 0 0

        # Reverse the part after but not                           k
        # including k, also efficiently.                     0 0 1 1 0 0 1 1
        seq[k + 1:] = seq[-1:k:-1]

"""

"""

def values_combinations(iterable):
    """
    >>> list(values_combinations(((3,),(1,3,4),(2,),(4,), (3,), (1,), (3,))))
    [[(1, 1), (2, 2), (0, 3), (3, 4)], [(1, 1), (2, 2), (4, 3), (3, 4)], [(1, 1), (2, 2), (6, 3), (3, 4)], [(5, 1), (2, 2), (0, 3), (1, 4)], [(5, 1), (2, 2), (0, 3), (3, 4)], [(5, 1), (2, 2), (1, 3), (3, 4)], [(5, 1), (2, 2), (4, 3), (1, 4)], [(5, 1), (2, 2), (4, 3), (3, 4)], [(5, 1), (2, 2), (6, 3), (1, 4)], [(5, 1), (2, 2), (6, 3), (3, 4)]]

        implemented to split ambiguous topologies to unique topologies
    :param iterable:
    :return:
    """
    pool = tuple(iterable)
    unique_items = set()
    for it in pool:
        unique_items.update(it)

    n = len(pool)
    r = len(unique_items)
    assert r <= n, str(iterable)

    values_map = dict()
    for val in unique_items:
        for index, it in enumerate(pool):
            if val in it:
                indexes_of_value = values_map.setdefault(val, list())
                indexes_of_value.append(index)

    values_items = list(values_map.items())

    for combination in product(values_map.values()):
        if len(set(combination)) == r:
            fields= [] #[None] * n
            for index, meta_index in enumerate(combination):
                 val, indexes_of_value = values_items[index]
                 fields.append((meta_index,val))
            yield fields #sorted(fields, key=lambda x: x[0])

def product(iterable):
    result = [[]]
    for pool in iterable:
        result = [x + [y] for x in result for y in pool]
    return result

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    seq = ((3,),(1,3,4),(2,),(4,), (3,), (1,), (3,))
    # seq = ((), (1, 3), (2,), (3,), (), (), (), (), (), (1,), (), (1,))
    print("\n".join(str(combo) for combo in values_combinations(seq)))