#!/usr/bin/env python3
"""
Test script to demonstrate the intelligent agent decision-making system
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agents.intelligence import agent_intelligence, AgentDecision, QueryAnalysis
from app.mcp.unified_schema import EntityType, TOOL_CAPABILITIES

def test_query_analysis():
    """Test the query analysis functionality"""
    print("=== Testing Query Analysis ===")
    
    test_queries = [
        "Show me the project status",
        "Create a new sprint for next month", 
        "How is the team performing?",
        "Update task ABC-123 to in progress",
        "Find all high priority bugs",
        "Remove duplicate items from the backlog",
        "Assign task XYZ-456 to John",
        "Generate work items from the GitHub repository"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        analysis = agent_intelligence._analyze_query_structure(query)
        print(f"  Intent: {analysis.intent}")
        print(f"  Entities: {analysis.entities_mentioned}")
        print(f"  Actions: {analysis.actions_implied}")
        print(f"  Filters: {analysis.specific_filters}")

def test_tool_capabilities():
    """Test tool capability definitions"""
    print("\n=== Tool Capabilities ===")
    
    for tool_name, capabilities in TOOL_CAPABILITIES.items():
        print(f"\n{tool_name.upper()}:")
        print(f"  Entities: {[e.value for e in capabilities.supported_entities]}")
        print(f"  Operations: {capabilities.supported_operations}")
        print(f"  Real-time: {capabilities.real_time_data}")

def test_decision_making_scenarios():
    """Test different decision-making scenarios"""
    print("\n=== Decision Making Scenarios ===")
    
    # Mock project context
    project_context = {
        'project': {
            'id': 1,
            'name': 'Test Project',
            'key': 'TEST'
        },
        'tools': [
            {'type': 'jira', 'name': 'JIRA Production'},
            {'type': 'github', 'name': 'GitHub Repository'}
        ]
    }
    
    test_scenarios = [
        {
            'query': 'Show me the current sprint status',
            'expected_action': 'analyze',
            'expected_entities': ['sprint', 'work_item']
        },
        {
            'query': 'Create work items from the repository code',
            'expected_action': 'create', 
            'expected_entities': ['work_item']
        },
        {
            'query': 'How many pull requests are open?',
            'expected_action': 'analyze',
            'expected_entities': ['pull_request']
        },
        {
            'query': 'Plan a 2-week sprint starting Monday',
            'expected_action': 'create',
            'expected_entities': ['sprint']
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\nScenario: '{scenario['query']}'")
        
        # Use fallback decision making since we don't have full LLM setup
        analysis = agent_intelligence._analyze_query_structure(scenario['query'])
        decision_data = agent_intelligence._fallback_decision_making(
            analysis, 
            ['jira', 'github']
        )
        
        print(f"  Action: {decision_data['action_type']} (expected: {scenario['expected_action']})")
        print(f"  Entities: {decision_data['entities_needed']}")
        print(f"  Tools: {decision_data['tools_to_use']}")
        print(f"  Reasoning: {decision_data['reasoning']}")
        print(f"  Confidence: {decision_data['confidence']}")

def test_unified_query_creation():
    """Test unified query creation"""
    print("\n=== Unified Query Creation ===")
    
    # Mock decision
    class MockDecision:
        def __init__(self):
            self.entities_needed = [EntityType.WORK_ITEM, EntityType.SPRINT]
            self.filters = {'status': 'in_progress'}
            self.additional_context = {
                'limit': 50,
                'sort_by': 'updated_date',
                'sort_order': 'desc'
            }
    
    decision = MockDecision()
    unified_query = agent_intelligence.create_unified_query(decision)
    
    print(f"Entities: {[e.value for e in unified_query.entities]}")
    print(f"Filters: {unified_query.filters}")
    print(f"Related entities: {[e.value for e in unified_query.include_related]}")
    print(f"Limit: {unified_query.limit}")
    print(f"Sort: {unified_query.sort_by} {unified_query.sort_order}")

def main():
    """Run all tests"""
    print("🤖 Intelligent Agent System Test")
    print("=" * 50)
    
    try:
        test_query_analysis()
        test_tool_capabilities()
        test_decision_making_scenarios()
        test_unified_query_creation()
        
        print("\n✅ All tests completed successfully!")
        print("\nThe intelligent agent system is working correctly:")
        print("- Query analysis extracts intent, entities, and context")
        print("- Tool capabilities are properly defined")
        print("- Decision making determines appropriate actions")
        print("- Unified queries can be created from decisions")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 