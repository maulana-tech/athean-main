// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";

/// @title VisitorWitness
/// @notice Records demo/visitor scenario witnesses on-chain.
///         total() is polled by the frontend CouncilPulse widget.
contract VisitorWitness is AccessControl {
    bytes32 public constant WITNESS_ROLE = keccak256("WITNESS_ROLE");

    struct Visit {
        bytes32 visitHash;
        string scenario;
        uint256 timestamp;
        address visitor;
    }

    uint256 private _count;
    mapping(uint256 => Visit) private _visits;

    event Witnessed(
        uint256 indexed index, bytes32 indexed visitHash, string scenario, address visitor
    );

    constructor(
        address admin
    ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(WITNESS_ROLE, admin);
    }

    function witness(
        bytes32 visitHash,
        string calldata scenario
    ) external onlyRole(WITNESS_ROLE) {
        uint256 index = _count++;
        _visits[index] = Visit({
            visitHash: visitHash,
            scenario: scenario,
            timestamp: block.timestamp,
            visitor: msg.sender
        });
        emit Witnessed(index, visitHash, scenario, msg.sender);
    }

    function total() external view returns (uint256) {
        return _count;
    }

    function getVisit(
        uint256 index
    ) external view returns (Visit memory) {
        require(index < _count, "out of range");
        return _visits[index];
    }
}
