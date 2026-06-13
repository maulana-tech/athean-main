// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";

/// @title ThesisRegistry
/// @notice Append-only registry of trade theses produced by the council.
contract ThesisRegistry is AccessControl {
    bytes32 public constant WRITER_ROLE = keccak256("WRITER_ROLE");

    struct Thesis {
        bytes32 contentHash;
        string thesisId;
        string marketId;
        string ipfsCid;
        uint256 registeredAt;
        address author;
    }

    uint256 private _count;
    mapping(uint256 => Thesis) private _theses;
    mapping(bytes32 => uint256) private _hashToSlot; // 0 = absent, else index+1

    event ThesisRegistered(uint256 indexed index, bytes32 indexed contentHash, string thesisId);

    constructor(
        address admin
    ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(WRITER_ROLE, admin);
    }

    function register(
        bytes32 contentHash,
        string calldata thesisId,
        string calldata marketId,
        string calldata ipfsCid
    ) external onlyRole(WRITER_ROLE) returns (uint256 index) {
        require(_hashToSlot[contentHash] == 0, "already registered");
        index = _count++;
        _theses[index] = Thesis({
            contentHash: contentHash,
            thesisId: thesisId,
            marketId: marketId,
            ipfsCid: ipfsCid,
            registeredAt: block.timestamp,
            author: msg.sender
        });
        _hashToSlot[contentHash] = index + 1;
        emit ThesisRegistered(index, contentHash, thesisId);
    }

    function total() external view returns (uint256) {
        return _count;
    }

    function thesis(
        uint256 index
    ) external view returns (Thesis memory) {
        require(index < _count, "out of range");
        return _theses[index];
    }

    function indexByHash(
        bytes32 contentHash
    ) external view returns (uint256) {
        uint256 slot = _hashToSlot[contentHash];
        require(slot != 0, "not found");
        return slot - 1;
    }
}
