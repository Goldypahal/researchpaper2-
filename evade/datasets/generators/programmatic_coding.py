"""
Programmatic Coding Generator for EVADE.
Produces verified coding challenges containing:
- Problem specification
- Function signature & starter code
- Reference solution verified against test cases
- Automated test assertions
All 25 templates are verified by executing assertions during generation.
"""

from typing import Any, Dict, List
from ..schema import EVADEItem, SourceMeta, ContaminationMeta
from ..pipeline.context_builder import build_contexts

CODING_TEMPLATES = [
    {
        "name": "is_palindrome_str",
        "doc": "Write a Python function `is_palindrome_str(s: str) -> bool` that returns True if the string is a palindrome (ignoring casing and non-alphanumeric characters), and False otherwise.",
        "starter": "def is_palindrome_str(s: str) -> bool:\n    # Write your solution here\n    pass",
        "solution": (
            "def is_palindrome_str(s: str) -> bool:\n"
            "    cleaned = ''.join(c.lower() for c in s if c.isalnum())\n"
            "    return cleaned == cleaned[::-1]"
        ),
        "tests": [
            "assert is_palindrome_str('A man, a plan, a canal: Panama') == True",
            "assert is_palindrome_str('race a car') == False",
            "assert is_palindrome_str('Was it a car or a cat I saw?') == True",
            "assert is_palindrome_str('No lemon, no melon') == True",
            "assert is_palindrome_str('hello world') == False",
        ],
        "subdomain": "string_processing",
        "diff": "easy",
    },
    {
        "name": "count_vowels_consonants",
        "doc": "Write a Python function `count_vowels_consonants(text: str) -> tuple[int, int]` that returns a tuple (vowels_count, consonants_count) for ASCII letters in the input string.",
        "starter": "def count_vowels_consonants(text: str) -> tuple:\n    # Write your solution here\n    pass",
        "solution": (
            "def count_vowels_consonants(text: str) -> tuple:\n"
            "    v = sum(1 for c in text.lower() if c in 'aeiou')\n"
            "    c = sum(1 for c in text.lower() if c.isalpha() and c not in 'aeiou')\n"
            "    return (v, c)"
        ),
        "tests": [
            "assert count_vowels_consonants('Hello World') == (3, 7)",
            "assert count_vowels_consonants('Python') == (1, 5)",
            "assert count_vowels_consonants('AEIOU') == (5, 0)",
            "assert count_vowels_consonants('12345!@#$') == (0, 0)",
        ],
        "subdomain": "string_processing",
        "diff": "easy",
    },
    {
        "name": "two_sum_indices",
        "doc": "Write a Python function `two_sum_indices(nums: list[int], target: int) -> list[int]` that returns the 0-based indices of the two numbers in `nums` that add up to `target`. Assume exactly one solution exists.",
        "starter": "def two_sum_indices(nums: list, target: int) -> list:\n    # Write your solution here\n    pass",
        "solution": (
            "def two_sum_indices(nums: list, target: int) -> list:\n"
            "    lookup = {}\n"
            "    for i, num in enumerate(nums):\n"
            "        comp = target - num\n"
            "        if comp in lookup:\n"
            "            return [lookup[comp], i]\n"
            "        lookup[num] = i\n"
            "    return []"
        ),
        "tests": [
            "assert two_sum_indices([2, 7, 11, 15], 9) == [0, 1]",
            "assert two_sum_indices([3, 2, 4], 6) == [1, 2]",
            "assert two_sum_indices([3, 3], 6) == [0, 1]",
            "assert two_sum_indices([10, -2, 5, 8], 3) == [1, 2]",
        ],
        "subdomain": "hash_maps",
        "diff": "easy",
    },
    {
        "name": "find_missing_number",
        "doc": "Write a Python function `find_missing_number(nums: list[int]) -> int` that takes a list of `n` distinct numbers in the range `[0, n]` and returns the only number in the range missing from the list.",
        "starter": "def find_missing_number(nums: list) -> int:\n    # Write your solution here\n    pass",
        "solution": (
            "def find_missing_number(nums: list) -> int:\n"
            "    n = len(nums)\n"
            "    expected = n * (n + 1) // 2\n"
            "    return expected - sum(nums)"
        ),
        "tests": [
            "assert find_missing_number([3, 0, 1]) == 2",
            "assert find_missing_number([0, 1]) == 2",
            "assert find_missing_number([9, 6, 4, 2, 3, 5, 7, 0, 1]) == 8",
            "assert find_missing_number([0]) == 1",
        ],
        "subdomain": "math_algorithms",
        "diff": "easy",
    },
    {
        "name": "flatten_nested_list",
        "doc": "Write a Python function `flatten_nested_list(lst: list) -> list` that recursively flattens an arbitrarily nested list of integers into a single flat list.",
        "starter": "def flatten_nested_list(lst: list) -> list:\n    # Write your solution here\n    pass",
        "solution": (
            "def flatten_nested_list(lst: list) -> list:\n"
            "    res = []\n"
            "    for x in lst:\n"
            "        if isinstance(x, list):\n"
            "            res.extend(flatten_nested_list(x))\n"
            "        else:\n"
            "            res.append(x)\n"
            "    return res"
        ),
        "tests": [
            "assert flatten_nested_list([1, [2, [3, 4], 5], 6]) == [1, 2, 3, 4, 5, 6]",
            "assert flatten_nested_list([[], [1], [[2]]]) == [1, 2]",
            "assert flatten_nested_list([1, 2, 3]) == [1, 2, 3]",
            "assert flatten_nested_list([]) == []",
        ],
        "subdomain": "recursion",
        "diff": "medium",
    },
    {
        "name": "longest_consecutive_run",
        "doc": "Write a Python function `longest_consecutive_run(nums: list[int]) -> int` that returns the length of the longest consecutive elements sequence in an unsorted list of integers in O(n) time.",
        "starter": "def longest_consecutive_run(nums: list) -> int:\n    # Write your solution here\n    pass",
        "solution": (
            "def longest_consecutive_run(nums: list) -> int:\n"
            "    num_set = set(nums)\n"
            "    longest = 0\n"
            "    for n in num_set:\n"
            "        if n - 1 not in num_set:\n"
            "            cur = n\n"
            "            streak = 1\n"
            "            while cur + 1 in num_set:\n"
            "                cur += 1\n"
            "                streak += 1\n"
            "            longest = max(longest, streak)\n"
            "    return longest"
        ),
        "tests": [
            "assert longest_consecutive_run([100, 4, 200, 1, 3, 2]) == 4",
            "assert longest_consecutive_run([0, 3, 7, 2, 5, 8, 4, 6, 0, 1]) == 9",
            "assert longest_consecutive_run([]) == 0",
            "assert longest_consecutive_run([5]) == 1",
        ],
        "subdomain": "hash_sets",
        "diff": "medium",
    },
    {
        "name": "compress_string",
        "doc": "Write a Python function `compress_string(s: str) -> str` that performs basic string compression using the counts of repeated characters. If the compressed string is not smaller than original, return the original string.",
        "starter": "def compress_string(s: str) -> str:\n    # Write your solution here\n    pass",
        "solution": (
            "def compress_string(s: str) -> str:\n"
            "    if not s:\n"
            "        return ''\n"
            "    res = []\n"
            "    cnt = 1\n"
            "    for i in range(1, len(s)):\n"
            "        if s[i] == s[i - 1]:\n"
            "            cnt += 1\n"
            "        else:\n"
            "            res.append(s[i - 1] + str(cnt))\n"
            "            cnt = 1\n"
            "    res.append(s[-1] + str(cnt))\n"
            "    compressed = ''.join(res)\n"
            "    return compressed if len(compressed) < len(s) else s"
        ),
        "tests": [
            "assert compress_string('aabcccccaaa') == 'a2b1c5a3'",
            "assert compress_string('abcdef') == 'abcdef'",
            "assert compress_string('aabb') == 'aabb'",
            "assert compress_string('aaaaaa') == 'a6'",
        ],
        "subdomain": "string_processing",
        "diff": "medium",
    },
    {
        "name": "matrix_transpose",
        "doc": "Write a Python function `matrix_transpose(matrix: list[list[int]]) -> list[list[int]]` that returns the transpose of a given 2D integer matrix.",
        "starter": "def matrix_transpose(matrix: list) -> list:\n    # Write your solution here\n    pass",
        "solution": (
            "def matrix_transpose(matrix: list) -> list:\n"
            "    if not matrix or not matrix[0]:\n"
            "        return []\n"
            "    return [[matrix[r][c] for r in range(len(matrix))] for c in range(len(matrix[0]))]"
        ),
        "tests": [
            "assert matrix_transpose([[1, 2, 3], [4, 5, 6]]) == [[1, 4], [2, 5], [3, 6]]",
            "assert matrix_transpose([[1, 2], [3, 4], [5, 6]]) == [[1, 3, 5], [2, 4, 6]]",
            "assert matrix_transpose([[7]]) == [[7]]",
        ],
        "subdomain": "matrices",
        "diff": "easy",
    },
    {
        "name": "valid_parentheses_check",
        "doc": "Write a Python function `valid_parentheses_check(s: str) -> bool` that determines if an input string containing '(', ')', '{', '}', '[' and ']' is valid.",
        "starter": "def valid_parentheses_check(s: str) -> bool:\n    # Write your solution here\n    pass",
        "solution": (
            "def valid_parentheses_check(s: str) -> bool:\n"
            "    stack = []\n"
            "    mapping = {')': '(', '}': '{', ']': '['}\n"
            "    for ch in s:\n"
            "        if ch in mapping.values():\n"
            "            stack.append(ch)\n"
            "        elif ch in mapping:\n"
            "            if not stack or stack.pop() != mapping[ch]:\n"
            "                return False\n"
            "    return len(stack) == 0"
        ),
        "tests": [
            "assert valid_parentheses_check('()[]{}') == True",
            "assert valid_parentheses_check('(]') == False",
            "assert valid_parentheses_check('([{}])') == True",
            "assert valid_parentheses_check('(') == False",
        ],
        "subdomain": "stacks",
        "diff": "easy",
    },
    {
        "name": "find_kth_largest",
        "doc": "Write a Python function `find_kth_largest(nums: list[int], k: int) -> int` that returns the k-th largest element in an unsorted array.",
        "starter": "def find_kth_largest(nums: list, k: int) -> int:\n    # Write your solution here\n    pass",
        "solution": (
            "def find_kth_largest(nums: list, k: int) -> int:\n"
            "    return sorted(nums, reverse=True)[k - 1]"
        ),
        "tests": [
            "assert find_kth_largest([3, 2, 1, 5, 6, 4], 2) == 5",
            "assert find_kth_largest([3, 2, 3, 1, 2, 4, 5, 5, 6], 4) == 4",
            "assert find_kth_largest([1], 1) == 1",
        ],
        "subdomain": "sorting",
        "diff": "easy",
    },
    {
        "name": "fibonacci_number",
        "doc": "Write a Python function `fibonacci_number(n: int) -> int` that returns the n-th Fibonacci number where fib(0) = 0 and fib(1) = 1.",
        "starter": "def fibonacci_number(n: int) -> int:\n    # Write your solution here\n    pass",
        "solution": (
            "def fibonacci_number(n: int) -> int:\n"
            "    if n <= 0:\n"
            "        return 0\n"
            "    elif n == 1:\n"
            "        return 1\n"
            "    a, b = 0, 1\n"
            "    for _ in range(2, n + 1):\n"
            "        a, b = b, a + b\n"
            "    return b"
        ),
        "tests": [
            "assert fibonacci_number(0) == 0",
            "assert fibonacci_number(1) == 1",
            "assert fibonacci_number(7) == 13",
            "assert fibonacci_number(10) == 55",
        ],
        "subdomain": "dynamic_programming",
        "diff": "easy",
    },
    {
        "name": "is_anagram_pair",
        "doc": "Write a Python function `is_anagram_pair(s: str, t: str) -> bool` that returns True if `t` is an anagram of `s` (case-insensitive and ignoring whitespace), and False otherwise.",
        "starter": "def is_anagram_pair(s: str, t: str) -> bool:\n    # Write your solution here\n    pass",
        "solution": (
            "def is_anagram_pair(s: str, t: str) -> bool:\n"
            "    s_clean = sorted(c.lower() for c in s if not c.isspace())\n"
            "    t_clean = sorted(c.lower() for c in t if not c.isspace())\n"
            "    return s_clean == t_clean"
        ),
        "tests": [
            "assert is_anagram_pair('listen', 'silent') == True",
            "assert is_anagram_pair('rail safety', 'fairy tales') == True",
            "assert is_anagram_pair('rat', 'car') == False",
            "assert is_anagram_pair('Dormitory', 'Dirty Room') == True",
        ],
        "subdomain": "string_processing",
        "diff": "easy",
    },
    {
        "name": "binary_search_index",
        "doc": "Write a Python function `binary_search_index(arr: list[int], target: int) -> int` that performs binary search on a sorted ascending list and returns the index of `target`, or -1 if not found.",
        "starter": "def binary_search_index(arr: list, target: int) -> int:\n    # Write your solution here\n    pass",
        "solution": (
            "def binary_search_index(arr: list, target: int) -> int:\n"
            "    low, high = 0, len(arr) - 1\n"
            "    while low <= high:\n"
            "        mid = (low + high) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        elif arr[mid] < target:\n"
            "            low = mid + 1\n"
            "        else:\n"
            "            high = mid - 1\n"
            "    return -1"
        ),
        "tests": [
            "assert binary_search_index([1, 3, 5, 7, 9, 11], 7) == 3",
            "assert binary_search_index([1, 3, 5, 7, 9, 11], 2) == -1",
            "assert binary_search_index([10], 10) == 0",
            "assert binary_search_index([], 5) == -1",
        ],
        "subdomain": "binary_search",
        "diff": "easy",
    },
    {
        "name": "reverse_words_sentence",
        "doc": "Write a Python function `reverse_words_sentence(sentence: str) -> str` that returns the words in the sentence in reverse order, separated by a single space, with leading and trailing spaces removed.",
        "starter": "def reverse_words_sentence(sentence: str) -> str:\n    # Write your solution here\n    pass",
        "solution": (
            "def reverse_words_sentence(sentence: str) -> str:\n"
            "    words = sentence.split()\n"
            "    return ' '.join(reversed(words))"
        ),
        "tests": [
            "assert reverse_words_sentence('the sky is blue') == 'blue is sky the'",
            "assert reverse_words_sentence('  hello world  ') == 'world hello'",
            "assert reverse_words_sentence('a good   example') == 'example good a'",
        ],
        "subdomain": "string_processing",
        "diff": "easy",
    },
    {
        "name": "max_subarray_sum",
        "doc": "Write a Python function `max_subarray_sum(nums: list[int]) -> int` that finds the contiguous subarray with the largest sum and returns its sum.",
        "starter": "def max_subarray_sum(nums: list) -> int:\n    # Write your solution here\n    pass",
        "solution": (
            "def max_subarray_sum(nums: list) -> int:\n"
            "    if not nums:\n"
            "        return 0\n"
            "    max_so_far = current_max = nums[0]\n"
            "    for x in nums[1:]:\n"
            "        current_max = max(x, current_max + x)\n"
            "        max_so_far = max(max_so_far, current_max)\n"
            "    return max_so_far"
        ),
        "tests": [
            "assert max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6",
            "assert max_subarray_sum([1]) == 1",
            "assert max_subarray_sum([5, 4, -1, 7, 8]) == 23",
            "assert max_subarray_sum([-5, -2, -8]) == -2",
        ],
        "subdomain": "dynamic_programming",
        "diff": "medium",
    },
    {
        "name": "rotate_list_right",
        "doc": "Write a Python function `rotate_list_right(nums: list[int], k: int) -> list[int]` that rotates a list of numbers to the right by `k` steps without modifying the original list.",
        "starter": "def rotate_list_right(nums: list, k: int) -> list:\n    # Write your solution here\n    pass",
        "solution": (
            "def rotate_list_right(nums: list, k: int) -> list:\n"
            "    if not nums:\n"
            "        return []\n"
            "    k = k % len(nums)\n"
            "    return nums[-k:] + nums[:-k] if k != 0 else list(nums)"
        ),
        "tests": [
            "assert rotate_list_right([1, 2, 3, 4, 5, 6, 7], 3) == [5, 6, 7, 1, 2, 3, 4]",
            "assert rotate_list_right([-1, -100, 3, 99], 2) == [3, 99, -1, -100]",
            "assert rotate_list_right([1, 2], 5) == [2, 1]",
        ],
        "subdomain": "arrays",
        "diff": "easy",
    },
    {
        "name": "is_power_of_two",
        "doc": "Write a Python function `is_power_of_two(n: int) -> bool` that returns True if the integer `n` is a power of two (i.e., n == 2^x for some non-negative integer x), and False otherwise.",
        "starter": "def is_power_of_two(n: int) -> bool:\n    # Write your solution here\n    pass",
        "solution": (
            "def is_power_of_two(n: int) -> bool:\n"
            "    return n > 0 and (n & (n - 1)) == 0"
        ),
        "tests": [
            "assert is_power_of_two(1) == True",
            "assert is_power_of_two(16) == True",
            "assert is_power_of_two(3) == False",
            "assert is_power_of_two(0) == False",
            "assert is_power_of_two(-8) == False",
        ],
        "subdomain": "bit_manipulation",
        "diff": "easy",
    },
    {
        "name": "group_anagrams_list",
        "doc": "Write a Python function `group_anagrams_list(strs: list[str]) -> list[list[str]]` that groups anagrams together. Sublists should be sorted by first element for determinism.",
        "starter": "def group_anagrams_list(strs: list) -> list:\n    # Write your solution here\n    pass",
        "solution": (
            "def group_anagrams_list(strs: list) -> list:\n"
            "    from collections import defaultdict\n"
            "    d = defaultdict(list)\n"
            "    for s in strs:\n"
            "        key = ''.join(sorted(s))\n"
            "        d[key].append(s)\n"
            "    res = [sorted(group) for group in d.values()]\n"
            "    return sorted(res)"
        ),
        "tests": [
            "assert group_anagrams_list(['eat', 'tea', 'tan', 'ate', 'nat', 'bat']) == [['ate', 'eat', 'tea'], ['bat'], ['nat', 'tan']]",
            "assert group_anagrams_list(['']) == [['']]",
            "assert group_anagrams_list(['a']) == [['a']]",
        ],
        "subdomain": "hash_maps",
        "diff": "medium",
    },
    {
        "name": "climbing_stairs_ways",
        "doc": "Write a Python function `climbing_stairs_ways(n: int) -> int` that returns the number of distinct ways to climb to the top of a staircase of `n` steps, given that you can climb either 1 or 2 steps at each stride.",
        "starter": "def climbing_stairs_ways(n: int) -> int:\n    # Write your solution here\n    pass",
        "solution": (
            "def climbing_stairs_ways(n: int) -> int:\n"
            "    if n <= 2:\n"
            "        return max(1, n)\n"
            "    a, b = 1, 2\n"
            "    for _ in range(3, n + 1):\n"
            "        a, b = b, a + b\n"
            "    return b"
        ),
        "tests": [
            "assert climbing_stairs_ways(2) == 2",
            "assert climbing_stairs_ways(3) == 3",
            "assert climbing_stairs_ways(5) == 8",
            "assert climbing_stairs_ways(1) == 1",
        ],
        "subdomain": "dynamic_programming",
        "diff": "easy",
    },
    {
        "name": "roman_to_integer",
        "doc": "Write a Python function `roman_to_integer(s: str) -> int` that converts a Roman numeral string (e.g. 'III', 'IV', 'IX', 'LVIII', 'MCMXCIV') to an integer.",
        "starter": "def roman_to_integer(s: str) -> int:\n    # Write your solution here\n    pass",
        "solution": (
            "def roman_to_integer(s: str) -> int:\n"
            "    val = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}\n"
            "    total = 0\n"
            "    for i in range(len(s)):\n"
            "        if i + 1 < len(s) and val[s[i]] < val[s[i + 1]]:\n"
            "            total -= val[s[i]]\n"
            "        else:\n"
            "            total += val[s[i]]\n"
            "    return total"
        ),
        "tests": [
            "assert roman_to_integer('III') == 3",
            "assert roman_to_integer('LVIII') == 58",
            "assert roman_to_integer('MCMXCIV') == 1994",
            "assert roman_to_integer('IX') == 9",
        ],
        "subdomain": "parsing",
        "diff": "easy",
    },
    {
        "name": "first_unique_char_index",
        "doc": "Write a Python function `first_unique_char_index(s: str) -> int` that finds the first non-repeating character in a string and returns its 0-based index. If it does not exist, return -1.",
        "starter": "def first_unique_char_index(s: str) -> int:\n    # Write your solution here\n    pass",
        "solution": (
            "def first_unique_char_index(s: str) -> int:\n"
            "    from collections import Counter\n"
            "    counts = Counter(s)\n"
            "    for idx, ch in enumerate(s):\n"
            "        if counts[ch] == 1:\n"
            "            return idx\n"
            "    return -1"
        ),
        "tests": [
            "assert first_unique_char_index('leetcode') == 0",
            "assert first_unique_char_index('loveleetcode') == 2",
            "assert first_unique_char_index('aabb') == -1",
        ],
        "subdomain": "hash_maps",
        "diff": "easy",
    },
    {
        "name": "pascals_triangle_row",
        "doc": "Write a Python function `pascals_triangle_row(row_index: int) -> list[int]` that returns the 0-indexed `row_index`-th row of Pascal's triangle. For example, row 0 is [1] and row 3 is [1, 3, 3, 1].",
        "starter": "def pascals_triangle_row(row_index: int) -> list:\n    # Write your solution here\n    pass",
        "solution": (
            "def pascals_triangle_row(row_index: int) -> list:\n"
            "    row = [1]\n"
            "    for _ in range(row_index):\n"
            "        row = [x + y for x, y in zip([0] + row, row + [0])]\n"
            "    return row"
        ),
        "tests": [
            "assert pascals_triangle_row(0) == [1]",
            "assert pascals_triangle_row(3) == [1, 3, 3, 1]",
            "assert pascals_triangle_row(4) == [1, 4, 6, 4, 1]",
        ],
        "subdomain": "math_algorithms",
        "diff": "easy",
    },
    {
        "name": "intersection_arrays",
        "doc": "Write a Python function `intersection_arrays(nums1: list[int], nums2: list[int]) -> list[int]` that returns a sorted list of unique numbers present in both `nums1` and `nums2`.",
        "starter": "def intersection_arrays(nums1: list, nums2: list) -> list:\n    # Write your solution here\n    pass",
        "solution": (
            "def intersection_arrays(nums1: list, nums2: list) -> list:\n"
            "    return sorted(list(set(nums1).intersection(set(nums2))))"
        ),
        "tests": [
            "assert intersection_arrays([1, 2, 2, 1], [2, 2]) == [2]",
            "assert intersection_arrays([4, 9, 5], [9, 4, 9, 8, 4]) == [4, 9]",
            "assert intersection_arrays([1, 3, 5], [2, 4, 6]) == []",
        ],
        "subdomain": "sets",
        "diff": "easy",
    },
    {
        "name": "chunk_list_by_size",
        "doc": "Write a Python function `chunk_list_by_size(lst: list, size: int) -> list[list]` that splits a list into chunks of length `size`. The final chunk may contain fewer elements if the list does not divide evenly.",
        "starter": "def chunk_list_by_size(lst: list, size: int) -> list:\n    # Write your solution here\n    pass",
        "solution": (
            "def chunk_list_by_size(lst: list, size: int) -> list:\n"
            "    if size <= 0:\n"
            "        return []\n"
            "    return [lst[i : i + size] for i in range(0, len(lst), size)]"
        ),
        "tests": [
            "assert chunk_list_by_size([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]",
            "assert chunk_list_by_size([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]",
            "assert chunk_list_by_size([], 3) == []",
        ],
        "subdomain": "arrays",
        "diff": "easy",
    },
    {
        "name": "merge_two_sorted_lists",
        "doc": "Write a Python function `merge_two_sorted_lists(l1: list[int], l2: list[int]) -> list[int]` that merges two sorted ascending lists into a single sorted list in O(n + m) time.",
        "starter": "def merge_two_sorted_lists(l1: list, l2: list) -> list:\n    # Write your solution here\n    pass",
        "solution": (
            "def merge_two_sorted_lists(l1: list, l2: list) -> list:\n"
            "    res = []\n"
            "    i = j = 0\n"
            "    while i < len(l1) and j < len(l2):\n"
            "        if l1[i] <= l2[j]:\n"
            "            res.append(l1[i])\n"
            "            i += 1\n"
            "        else:\n"
            "            res.append(l2[j])\n"
            "            j += 1\n"
            "    res.extend(l1[i:])\n"
            "    res.extend(l2[j:])\n"
            "    return res"
        ),
        "tests": [
            "assert merge_two_sorted_lists([1, 2, 4], [1, 3, 4]) == [1, 1, 2, 3, 4, 4]",
            "assert merge_two_sorted_lists([], []) == []",
            "assert merge_two_sorted_lists([], [0]) == [0]",
        ],
        "subdomain": "two_pointers",
        "diff": "easy",
    },
]


def verify_code_solution(solution_code: str, test_lines: List[str]) -> bool:
    """Executes reference solution and asserts to guarantee 100% correctness."""
    env: Dict[str, Any] = {}
    try:
        exec(solution_code, env)
        for t in test_lines:
            exec(t, env)
        return True
    except Exception as e:
        print(f"Code verification error: {e}")
        return False


def generate_programmatic_coding(count: int = 25, start_index: int = 1) -> List[EVADEItem]:
    """Generates verified coding tasks with starter code and test suites."""
    items: List[EVADEItem] = []
    total_avail = len(CODING_TEMPLATES)
    actual_count = min(count, total_avail)

    for i in range(actual_count):
        tmpl = CODING_TEMPLATES[i]
        is_verified = verify_code_solution(tmpl["solution"], tmpl["tests"])
        assert is_verified, f"Reference solution failed assertions for {tmpl['name']}"

        task_id = f"coding_prog_{start_index + i:04d}"
        core_q = (
            f"{tmpl['doc']}\n\n"
            f"Starter code:\n```python\n{tmpl['starter']}\n```\n\n"
            f"Example test assertion:\n`{tmpl['tests'][0]}`"
        )
        contexts = build_contexts(domain="coding", task_id=task_id, is_synthetic_benchmark=False)

        item = EVADEItem(
            task_id=task_id,
            domain="coding",
            subdomain=tmpl["subdomain"],
            source=SourceMeta(
                type="programmatic",
                dataset="evade_coding_generator",
                source_id=f"prog_code_{tmpl['name']}",
            ),
            core_question=core_q,
            ground_truth=tmpl["solution"],
            difficulty=tmpl["diff"],
            answer_type="code_tests",
            starter_code=tmpl["starter"],
            test_cases=[{"assert": t} for t in tmpl["tests"]],
            contamination=ContaminationMeta(
                risk="low",
                freshness_date="2026-09-23",
                notes="Generated programmatically with automated unit assertion verification",
            ),
            contexts=contexts,
            metadata={"function_name": tmpl["name"], "num_tests": len(tmpl["tests"])},
        )
        items.append(item)

    return items
