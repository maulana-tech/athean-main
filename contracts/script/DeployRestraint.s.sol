// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/ProofOfRestraint.sol";
import "../src/NoTradeAlpha.sol";
import "../src/VisitorWitness.sol";

/// @notice Deploys the restraint + counterfactual contracts on Mantle Sepolia.
/// @dev Run via: just deploy-restraint
///      Populate deployments/mantle-sepolia.json with the printed addresses.
///      Set PROOF_OF_RESTRAINT_ADDRESS in env to activate chain writes in areopagus.
contract DeployRestraint is Script {
    function run() external {
        uint256 pk = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(pk);

        vm.startBroadcast(pk);

        ProofOfRestraint por = new ProofOfRestraint(deployer);
        NoTradeAlpha nta = new NoTradeAlpha(deployer);
        VisitorWitness vw = new VisitorWitness(deployer);

        vm.stopBroadcast();

        console.log("=== Restraint Deployment (Mantle Sepolia) ===");
        console.log("ProofOfRestraint:", address(por));
        console.log("NoTradeAlpha:    ", address(nta));
        console.log("VisitorWitness:  ", address(vw));
        console.log("Deployer:        ", deployer);
        console.log("Block:           ", block.number);
        console.log("");
        console.log("Next: set PROOF_OF_RESTRAINT_ADDRESS =", address(por));
        console.log("      set NEXT_PUBLIC_PROOF_OF_RESTRAINT_ADDRESS =", address(por));
        console.log("      set NEXT_PUBLIC_VISITOR_WITNESS_ADDRESS =", address(vw));
    }
}
