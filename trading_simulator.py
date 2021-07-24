import csv
import random
import time
from typing import Optional, Tuple

import cv2
import numpy as np


class TradingSimulator:
    def __init__(self,
                 n_max: int = 10,
                 n_min: int = 0,
                 n_ticks: int = 100,
                 t_update: float = 0.02,
                 image_shape: Tuple[int, int] = (250, 1000),
                 show_expected_value_line: bool = True):
        """Trading simulator.

        Overwrite number_generator and get_expected_value function to replace the number generator and its expected
        value.
        Currently, number_generator consists of two uniform distributions used as a multiplier to the previous value
        and penalize the market value from straying too far away from the intrinsic value.

        Warning: Will be bugged if while loop in pipeline takes longer than t_update (as buy/sell step may take
        multiple t_updates in time).

        Hotkeys:
            - c: Buy
            - v: Sell
            - s: Position status
            - q: Options
            - ESC: Quit simulator

        Args:
            n_max (int, optional): Maximum possible value from number generator. Defaults to 10.
            n_min (int, optional): Minimum number generator. Defaults to 0.
            n_ticks (int, optional): Number of ticks shown on screen. Defaults to 100.
            t_update (float, optional): Time between ticks. Defaults to 0.02.
            image_shape (Tuple[int, int], optional): Image shape (height, width). Defaults to (250, 1000).
            show_expected_value_line (bool, optional): Whether to visualise expected value in simulator. Defaults to
                True.
        """
        self.n_max = int(n_max)
        self.n_min = int(n_min)
        self.n_ticks = int(n_ticks)

        self.t_update = t_update
        self.image_shape = image_shape
        self.show_expected_value_line = show_expected_value_line

        self.trades = []
        self.possible_range = 9 * (self.n_max - self.n_min)
        self.expected_value = TradingSimulator.get_expected_value(n_max=n_max,
                                                                  n_min=n_min)

        self.BAR_WIDTH = self.image_shape[1] // self.n_ticks
        self.BAR_HEIGHT_MULTIPLIER = self.image_shape[0] / self.possible_range

        assert self.image_shape[1] % self.n_ticks == 0

    def __call__(self):
        run_simulator = True
        bought_position = None
        next_val = self.expected_value
        previous_step_time = time.time()  # Time step 0

        img = np.zeros((*self.image_shape, 3))
        transaction_made_in_tick = 0
        while run_simulator:
            next_val = TradingSimulator.number_generator(
                previous_value=next_val, expected_value=self.expected_value)
            cv2.imshow("Trading Simulator", img)

            k = cv2.waitKey(1)
            if k == 27:  # Use ESC key to stop simulator
                cv2.destroyAllWindows()
                break
            elif k == ord("c") and not transaction_made_in_tick:
                # Buy
                print(f"Bought at: {next_val}")
                if bought_position is None:
                    bought_position = [next_val]
                else:
                    bought_position.append(next_val)
                img = self.update(img, next_val=next_val, bought=True)
                # Assume can only buy once per candle
                transaction_made_in_tick = True
            elif k == ord(
                    "v"
            ) and bought_position is None and not transaction_made_in_tick:
                print("No bought shares.")
            elif k == ord("v") and not transaction_made_in_tick:
                # Sell
                img = self.update(img, next_val=next_val, sold=True)

                mean_bought_position = np.mean(bought_position)
                print(f"Sold at: {next_val}")
                print(
                    f"Profit: {mean_bought_position - next_val} (Buy: {mean_bought_position}, Sell: {next_val})"
                )
                self.trades.append({
                    "buy": mean_bought_position,
                    "sell": next_val
                })
                bought_position = None
                # Assume can only sell once per candle
                transaction_made_in_tick = True
            elif k == ord("s"):
                # Show position status
                print(
                    f"Position status: {np.mean(bought_position) if bought_position is not None else 0}"
                )
            elif k == ord("q"):
                print(
                    "c: Buy\nv: Sell\ns: Position status\nESC: Quit simulator")

            current_time = time.time()
            if current_time - previous_step_time > self.t_update:  # 1:
                print(f"Step: {next_val}")
                print(current_time - previous_step_time)
                previous_step_time = current_time
                if not transaction_made_in_tick:
                    img = self.update(img, next_val=next_val)
                transaction_made_in_tick = False

        # Log trades to CSV at end of simulation
        if self.trades:
            keys = self.trades[0].keys()
            with open('trades.csv', 'w', newline='') as output_file:
                writer = csv.DictWriter(output_file, keys)
                writer.writeheader()
                writer.writerows(self.trades)

    @staticmethod
    def number_generator(previous_value: int = 0,
                         expected_value: int = 0) -> int:
        if previous_value > expected_value:
            multiplier = previous_value * random.uniform(0.75, 1.1)
        else:
            multiplier = previous_value * random.uniform(0.9, 1.25)
        return int(multiplier)

    @staticmethod
    def get_expected_value(n_max: int, n_min: int):
        return int(4.5 * 10)

    def update(self,
               img,
               next_val: Optional[int] = None,
               bought=False,
               sold=False):
        # Update visualiser
        next_col = np.zeros((self.image_shape[0], self.BAR_WIDTH, 3))
        if bought:
            colour = (0, 255, 0)  # Green
        elif sold:
            colour = (0, 0, 255)  # Red

        # Show expected value
        if self.show_expected_value_line:
            next_col[int(self.expected_value *
                         self.BAR_HEIGHT_MULTIPLIER)] = (255, 0, 0)

        if bought or sold:
            if next_val > self.expected_value:
                next_col[int(self.expected_value *
                             self.BAR_HEIGHT_MULTIPLIER):int(
                                 (next_val - 1) *
                                 self.BAR_HEIGHT_MULTIPLIER)] = colour
            else:
                next_col[int((next_val - 1) * self.BAR_HEIGHT_MULTIPLIER
                             ):int(self.expected_value *
                                   self.BAR_HEIGHT_MULTIPLIER)] = colour

        # Show current value
        next_col[int(self.BAR_HEIGHT_MULTIPLIER * next_val)] = (255, 255, 255)

        img = np.delete(img, obj=np.s_[:self.BAR_WIDTH], axis=1)
        img = np.concatenate((img, next_col), axis=1)
        return img


def tuple_type(value: str):
    value = value.replace("(", "").replace(")", "").replace(" ", "")
    mapped_int = map(int, value.split(","))
    return tuple(mapped_int)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_max",
                        default=10,
                        type=int,
                        help="Maximum possible value from number generator.")
    parser.add_argument("--n_min",
                        default=0,
                        type=int,
                        help="Minimum possible value from number generator.")
    parser.add_argument("--n_ticks",
                        default=100,
                        type=int,
                        help="Number of ticks shown on screen.")
    parser.add_argument("--t_update",
                        default=0.02,
                        type=float,
                        help="Time between ticks.")
    parser.add_argument("--image_shape",
                        default=(250, 1000),
                        type=tuple_type,
                        help="Image shape with format height,width.")
    parser.add_argument(
        "--show_expected_value_line",
        default=True,
        type=bool,
        help="Whether to visualise expected value in simulator.")
    args = parser.parse_args()

    sim = TradingSimulator()
    sim()
