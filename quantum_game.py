import logging
import os
import webbrowser
from typing import Type

import numpy as np

import plot
import states
from algorithms import Algorithm, Exact, TDVP
from parameters import Parser
from tensor_networks import MPO, MPS


class QuantumGame(object):

    def __init__(self, args: Parser):
        self.args = args
        self.H = MPO.hamiltonian_from_rules(args.rules)
        self.initial_states = (
                [getattr(states, name)() for name in args.initial_states] +
                [MPS.from_file(file) for file in args.initial_state_files]
        )
        logging.basicConfig(level=logging.INFO)

    def start(self):
        args = self.args
        for index, initial_state in enumerate(self.initial_states):
            population = np.empty(
                [args.plot_steps, args.rules.ncells]
            )
            d_population = np.empty(
                [args.plot_steps, args.rules.ncells]
            )
            single_site_entropy = np.empty(
                [args.plot_steps, args.rules.ncells]
            )
            state_name: str
            if index < len(args.initial_states):
                state_name = args.initial_states[index]
            else:
                state_name = str(index)

            file_name = F"{state_name}_{args.rules.ncells}_{args.rules.distance}_{args.rules.activation_interval.start}_{args.rules.activation_interval.stop}_{args.algorithm}"

            logging.info('Preparing algorithm...')
            algorithm_choice: Type[Algorithm] = (
                Exact if args.algorithm == 'exact' else
                TDVP if args.algorithm == 'tdvp' else
                None
            )

            step_size = (
                args.step_size * args.plot_step_interval if args.algorithm == 'exact' else
                args.step_size
            )

            algorithm = algorithm_choice(
                psi_0=initial_state,
                H=self.H,
                step_size=step_size
            )

            for step in range(args.num_steps):
                if step % 100 == 0:
                    logging.info(F"Step {step} of {args.num_steps}")
                if step % args.plot_step_interval == 0:
                    plot_step = step // args.plot_step_interval
                    algorithm.measure(
                        population=population[plot_step, :],
                        d_population=d_population[plot_step, :],
                        single_site_entropy=single_site_entropy[plot_step, :],
                    )

                    # Backup all measured data to csv files
                    np.savetxt(
                        F"{args.plot_file_path}{file_name}-population.csv",
                        population[:plot_step, :],
                        delimiter=','
                    )
                    np.savetxt(
                        F"{args.plot_file_path}{file_name}-d_population.csv",
                        d_population[:plot_step, :],
                        delimiter=','
                    )
                    np.savetxt(
                        F"{args.plot_file_path}{file_name}-single_site_entropy.csv",
                        single_site_entropy[:plot_step, :],
                        delimiter=','
                    )

                    algorithm.psi.write_to_file(
                        F"data/{file_name}.npz")
                    if args.algorithm == 'exact':
                        algorithm.do_time_step()
                if args.algorithm != 'exact':
                    algorithm.do_time_step()
            # Create one plot for each format specified
            for format in args.file_formats:
                path = os.path.join(
                    os.getcwd(),
                    F"{args.plot_file_path}{file_name}.{format}"
                )
                heatmaps = []
                if args.plot_classical:
                    classical = Algorithm.classical_evolution(
                        first_column=d_population[0, :],
                        rules=args.rules,
                        plot_steps=args.plot_steps
                    )
                    heatmaps.append(classical)
                heatmaps += [
                    population,
                    d_population,
                    single_site_entropy
                ]
                # Save the plots to files
                plot.plot(heatmaps=heatmaps, path=path)
                if args.show:
                    # Show the plot files
                    webbrowser.open("file://" + path, new=2)