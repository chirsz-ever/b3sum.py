#!/usr/bin/env bash

set -e

cd "$(dirname "$(realpath "$0")")"

repeat() {
    awk -v s="$1" -v n="$2" 'BEGIN { for (i = 0; i < n; i++) printf("%s", s); }'
}

streq() {
    case $1 in "$2") return; esac
    return 1
}

test() {
    s1=$(printf "%s" "$1" | b3sum)
    s2=$(printf "%s" "$1" | ./b3sum.py)
    if [[ $s1 != "$s2" ]]; then
        echo "error: difference when hash \"$1\"" >&2
        echo "  b3sum:    $s1" >&2
        echo "  b3sum.py: $s2" >&2
        exit 1
    fi
}

test ""
test "abc"
test "IETF"
test "The quick brown fox jumps over the lazy dog"
test "$(repeat "a" 10)"
test "$(repeat "a" 55)"
test "$(repeat "a" 56)"
test "$(repeat "a" 64)"
test "$(repeat "a" 65)"
test "$(repeat "a" 100)"
test "$(repeat "a" 1000)"
test "$(repeat "a" 1024)"
test "$(repeat "a" 1025)"
test "$(repeat "a" 2000)"
test "$(repeat "a" 2048)"
test "$(repeat "a" 2049)"
test "$(repeat "a" 100000)"
