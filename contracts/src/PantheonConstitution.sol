// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title PantheonConstitution
/// @notice Immutable on-chain record of Athean trading system rules.
/// @dev Never upgradeable. Articles are sealed at construction and cannot
///      be modified. See docs/CONSTITUTION.md for canonical text.
contract PantheonConstitution {
    string public constant VERSION = "1.0.0";

    struct Article {
        string id;
        string body;
    }

    Article[] private _articles;
    uint256 public immutable sealedAt;
    address public immutable deployer;

    event ArticleSealed(uint256 indexed index, string id);

    constructor(string[] memory ids, string[] memory bodies) {
        require(ids.length == bodies.length, "length mismatch");
        require(ids.length > 0, "empty constitution");
        for (uint256 i = 0; i < ids.length; i++) {
            _articles.push(Article(ids[i], bodies[i]));
            emit ArticleSealed(i, ids[i]);
        }
        sealedAt = block.timestamp;
        deployer = msg.sender;
    }

    function articleCount() external view returns (uint256) {
        return _articles.length;
    }

    function article(uint256 index) external view returns (string memory id, string memory body) {
        require(index < _articles.length, "out of range");
        Article storage a = _articles[index];
        return (a.id, a.body);
    }

    function constitutionHash() external view returns (bytes32) {
        bytes memory packed;
        for (uint256 i = 0; i < _articles.length; i++) {
            packed = abi.encodePacked(packed, _articles[i].id, _articles[i].body);
        }
        return keccak256(packed);
    }
}
