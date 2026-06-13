// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library Roles {
    bytes32 internal constant ADMIN = keccak256("ADMIN");
    bytes32 internal constant OPERATOR = keccak256("OPERATOR");
    bytes32 internal constant COUNCIL = keccak256("COUNCIL");
    bytes32 internal constant AREOPAGUS = keccak256("AREOPAGUS");
    bytes32 internal constant PARTHENON = keccak256("PARTHENON");
    bytes32 internal constant ORACLE = keccak256("ORACLE");
    bytes32 internal constant RECORDER = keccak256("RECORDER_ROLE");
    bytes32 internal constant WRITER = keccak256("WRITER_ROLE");
    bytes32 internal constant ANCHOR = keccak256("ANCHOR_ROLE");
    bytes32 internal constant SCORER = keccak256("SCORER_ROLE");
    bytes32 internal constant WITNESS = keccak256("WITNESS_ROLE");
    bytes32 internal constant MINTER = keccak256("MINTER_ROLE");
    bytes32 internal constant RESOLVER = keccak256("RESOLVER_ROLE");
}
