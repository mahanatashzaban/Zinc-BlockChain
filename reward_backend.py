import time
import math

class RewardSystem:
    def __init__(self):
        self.staking_pool_total = 400_000_000
        self.rewards_per_year = 20_000_000
        self.start_time = int(time.time())
        self.stakers = {}  # { address: { 'amount': x, 'last_claimed': ts, 'total_claimed': y } }
        self.total_staked = 0

    def get_current_year(self):
        elapsed = int(time.time()) - self.start_time
        return elapsed // (365 * 24 * 3600)

    def get_annual_reward(self):
        year = self.get_current_year()
        return self.rewards_per_year * (0.95 ** year)

    def stake(self, address, amount):
        now = int(time.time())
        if address not in self.stakers:
            self.stakers[address] = {
                'amount': amount,
                'last_claimed': now,
                'total_claimed': 0
            }
        else:
            self.stakers[address]['amount'] += amount
        self.total_staked += amount

    def calculate_reward(self, address):
        now = int(time.time())
        if address not in self.stakers:
            return 0

        user = self.stakers[address]
        staked_duration = now - user['last_claimed']
        if staked_duration < 300:  # 5-minute reward interval
            return 0

        annual_reward = self.get_annual_reward()
        reward_pool = annual_reward / (365 * 24 * 3600) * staked_duration

        if self.total_staked == 0:
            return 0

        user_share = user['amount'] / self.total_staked
        return reward_pool * user_share

    def claim_reward(self, address):
        reward = self.calculate_reward(address)
        if reward > 0:
            self.stakers[address]['last_claimed'] = int(time.time())
            self.stakers[address]['total_claimed'] += reward
        return reward

    def get_stake_info(self, address):
        return self.stakers.get(address, {
            'amount': 0,
            'last_claimed': None,
            'total_claimed': 0
        })
