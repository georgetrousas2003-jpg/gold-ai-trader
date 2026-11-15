from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import json
from loguru import logger

from agents.core.base_agent import BaseAgent, AgentContext, AgentOutput
from agents.specialized.technical_analyst import TechnicalAnalystAgent
from agents.specialized.risk_manager import RiskManagerAgent
from agents.specialized.strategy_agent import StrategyAgent
from agents.specialized.execution_agent import ExecutionAgent
from agents.specialized.news_sentiment import NewsSentimentAgent
from agents.specialized.meta_learning import MetaLearningAgent


class ConsensusType(Enum):
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    UNANIMOUS = "unanimous"
    RISK_VETO = "risk_veto"


@dataclass
class OrchestratorConfig:
    consensus_type: ConsensusType = ConsensusType.WEIGHTED
    agent_weights: Dict[str, float] = field(default_factory=lambda: {
        "TechnicalAnalyst": 0.25,
        "RiskManager": 0.20,
        "StrategyAgent": 0.20,
        "ExecutionAgent": 0.10,
        "NewsSentimentAgent": 0.15,
        "MetaLearningAgent": 0.10,
    })
    min_confidence_threshold: float = 0.6
    risk_veto_enabled: bool = True
    max_concurrent_analysis: int = 3


class AgentOrchestrator:
    """Multi-agent orchestrator for Gold AI Trading System"""
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self.agents: Dict[str, BaseAgent] = {}
        self.analysis_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Dict[str, float]] = {}
        self._initialize_agents()
        
    def _initialize_agents(self):
        """Initialize all specialized agents"""
        agent_classes = {
            "TechnicalAnalyst": TechnicalAnalystAgent,
            "RiskManager": RiskManagerAgent,
            "StrategyAgent": StrategyAgent,
            "ExecutionAgent": ExecutionAgent,
            "NewsSentimentAgent": NewsSentimentAgent,
            "MetaLearningAgent": MetaLearningAgent,
        }
        
        for name, agent_class in agent_classes.items():
            try:
                self.agents[name] = agent_class()
                logger.info(f"Initialized agent: {name}")
            except Exception as e:
                logger.error(f"Failed to initialize {name}: {e}")
    
    async def analyze(self, context: AgentContext) -> Dict[str, Any]:
        """Run all agents and build consensus"""
        logger.info(f"Starting multi-agent analysis for {context.symbol}")
        
        # Run agents in parallel
        agent_outputs = await self._run_agents_parallel(context)
        
        # Build consensus
        consensus = self._build_consensus(agent_outputs, context)
        
        # Store for learning
        self._store_analysis(context, agent_outputs, consensus)
        
        return {
            "consensus": consensus,
            "agent_outputs": {name: output.to_dict() for name, output in agent_outputs.items()},
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": context.symbol
        }
    
    async def _run_agents_parallel(self, context: AgentContext) -> Dict[str, AgentOutput]:
        """Run all agents concurrently with semaphore"""
        semaphore = asyncio.Semaphore(self.config.max_concurrent_analysis)
        
        async def run_agent(name: str, agent: BaseAgent) -> tuple:
            async with semaphore:
                try:
                    output = await agent.analyze(context)
                    return name, output
                except Exception as e:
                    logger.error(f"Agent {name} failed: {e}")
                    return name, AgentOutput(
                        agent_name=name,
                        agent_type=agent.agent_type,
                        confidence=0.0,
                        signal="ERROR",
                        reasoning=str(e)
                    )
        
        tasks = [run_agent(name, agent) for name, agent in self.agents.items()]
        results = await asyncio.gather(*tasks)
        
        return dict(results)
    
    def _build_consensus(self, agent_outputs: Dict[str, AgentOutput], context: AgentContext) -> Dict[str, Any]:
        """Build consensus from agent outputs"""
        
        # Risk veto check
        if self.config.risk_veto_enabled:
            risk_output = agent_outputs.get("RiskManager")
            if risk_output and not risk_output.risk_metrics.get("can_trade", True):
                return {
                    "signal": "HOLD",
                    "confidence": 1.0,
                    "reasoning": "Risk Manager vetoed trade due to drawdown limits",
                    "vetoed_by": "RiskManager",
                    "details": risk_output.risk_metrics
                }
        
        # Weighted consensus
        if self.config.consensus_type == ConsensusType.WEIGHTED:
            return self._weighted_consensus(agent_outputs)
        elif self.config.consensus_type == ConsensusType.MAJORITY:
            return self._majority_consensus(agent_outputs)
        else:
            return self._weighted_consensus(agent_outputs)
    
    def _weighted_consensus(self, agent_outputs: Dict[str, AgentOutput]) -> Dict[str, Any]:
        """Calculate weighted consensus based on agent weights and confidence"""
        signal_scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        total_weight = 0.0
        reasoning_parts = []
        
        for name, output in agent_outputs.items():
            weight = self.config.agent_weights.get(name, 0.1)
            confidence = output.confidence
            effective_weight = weight * confidence
            
            if output.signal in signal_scores:
                signal_scores[output.signal] += effective_weight
            
            total_weight += effective_weight
            reasoning_parts.append(f"{name}: {output.signal} ({confidence:.0%}) - {output.reasoning[:100]}")
        
        # Normalize
        if total_weight > 0:
            for signal in signal_scores:
                signal_scores[signal] /= total_weight
        
        # Determine final signal
        final_signal = max(signal_scores, key=signal_scores.get)
        final_confidence = signal_scores[final_signal]
        
        # Check threshold
        if final_confidence < self.config.min_confidence_threshold:
            final_signal = "HOLD"
            final_confidence = 1.0 - final_confidence
        
        return {
            "signal": final_signal,
            "confidence": round(final_confidence, 3),
            "signal_scores": {k: round(v, 3) for k, v in signal_scores.items()},
            "reasoning": " | ".join(reasoning_parts),
            "method": "weighted_consensus"
        }
    
    def _majority_consensus(self, agent_outputs: Dict[str, AgentOutput]) -> Dict[str, Any]:
        """Simple majority voting"""
        votes = {"BUY": 0, "SELL": 0, "HOLD": 0}
        total_confidence = 0.0
        
        for output in agent_outputs.values():
            if output.signal in votes:
                votes[output.signal] += 1
            total_confidence += output.confidence
        
        final_signal = max(votes, key=votes.get)
        final_confidence = total_confidence / len(agent_outputs) if agent_outputs else 0
        
        return {
            "signal": final_signal,
            "confidence": round(final_confidence, 3),
            "votes": votes,
            "method": "majority_vote"
        }
    
    def _store_analysis(self, context: AgentContext, agent_outputs: Dict[str, AgentOutput], consensus: Dict[str, Any]):
        """Store analysis for performance tracking and meta-learning"""
        self.analysis_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": context.symbol,
            "price": context.current_price,
            "consensus": consensus,
            "agent_signals": {name: out.signal for name, out in agent_outputs.items()},
            "agent_confidences": {name: out.confidence for name, out in agent_outputs.items()}
        })
        
        # Keep last 1000 analyses
        if len(self.analysis_history) > 1000:
            self.analysis_history = self.analysis_history[-1000:]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance metrics for all agents"""
        return {
            "total_analyses": len(self.analysis_history),
            "agents": list(self.agents.keys()),
            "config": {
                "consensus_type": self.config.consensus_type.value,
                "agent_weights": self.config.agent_weights,
                "min_confidence_threshold": self.config.min_confidence_threshold
            }
        }
    
    async def update_agent_performance(self, trade_result: Dict[str, Any]):
        """Update agent performance based on trade outcomes"""
        # This would be called after trades close to update agent weights
        # For now, just log
        logger.info(f"Trade result for learning: {trade_result}")


# Backward compatibility
AgentContext = AgentContext
AgentOutput = AgentOutput
