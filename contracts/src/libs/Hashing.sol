// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

library Hashing {
    function signal(
        string calldata marketId,
        string calldata reasonCode,
        uint256 ts
    ) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(marketId, reasonCode, ts));
    }

    function thesis(
        string calldata thesisId,
        bytes calldata payload
    ) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(thesisId, payload));
    }

    function visit(
        address visitor,
        string calldata scenario,
        uint256 ts
    ) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(visitor, scenario, ts));
    }
}
