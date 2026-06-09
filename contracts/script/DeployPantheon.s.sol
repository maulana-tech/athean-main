// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/PantheonConstitution.sol";
import "../src/ThesisRegistry.sol";
import "../src/SignalRegistry.sol";
import "../src/erc8004/AgentPassport.sol";
import "../src/Parthenon.sol";
import "../src/Ostrakon.sol";

/// @notice Deploys the core Pantheon contracts on Mantle Sepolia.
/// @dev Run via: just deploy-mantle
///      Populate deployments/mantle-sepolia.json with the printed addresses.
contract DeployPantheon is Script {
    function run() external {
        uint256 pk      = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(pk);

        // Canonical constitution articles from docs/CONSTITUTION.md
        string[] memory ids    = new string[](5);
        string[] memory bodies = new string[](5);
        ids[0] = "II §1";   bodies[0] = "No position shall exceed five percent of total book equity.";
        ids[1] = "III §2";  bodies[1] = "Crypto-cluster exposure shall not exceed twelve percent at any time.";
        ids[2] = "IV §1";   bodies[2] = "No trade where 24-hour volume falls below fifty thousand USDC.";
        ids[3] = "V §3";    bodies[3] = "Politics positions shall not exceed four percent, sports three, science two.";
        ids[4] = "VI §1";   bodies[4] = "Kelly is taken at one-half. Never full. Never doubled.";

        vm.startBroadcast(pk);

        PantheonConstitution constitution = new PantheonConstitution(ids, bodies);
        ThesisRegistry       thesis       = new ThesisRegistry(deployer);
        SignalRegistry       signal       = new SignalRegistry(deployer);
        AgentPassport        passport     = new AgentPassport(deployer);
        Parthenon            parthenon    = new Parthenon(deployer);
        Ostrakon             ostrakon     = new Ostrakon(deployer);

        vm.stopBroadcast();

        console.log("=== Pantheon Deployment (Mantle Sepolia) ===");
        console.log("PantheonConstitution:", address(constitution));
        console.log("ThesisRegistry:      ", address(thesis));
        console.log("SignalRegistry:      ", address(signal));
        console.log("AgentPassport:       ", address(passport));
        console.log("Parthenon:           ", address(parthenon));
        console.log("Ostrakon:            ", address(ostrakon));
        console.log("Deployer:            ", deployer);
        console.log("Block:               ", block.number);
    }
}
