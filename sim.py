from manim import *
import numpy as np

DATA = {
    "Azithromycin":  {"alpha": 9.1,  "beta": 1.12, "color": BLUE},
    "Ciprofloxacin": {"alpha": 71.8, "beta": 2.46, "color": GREEN},
}

C_TREAT = 0.18
START_POP = 100 
DISH_R = 2.5
CELL_BOUND = 2.2

def get_p_divide(c, alpha, beta):
    return 1.0 / (1.0 + alpha * (c ** beta))

class BacterialCell(Dot):
    def __init__(self, pos, dish_center, color=WHITE):
        super().__init__(point=pos, radius=0.06, color=color, fill_opacity=0.8, stroke_width=2, stroke_color=color)
        self.dish_center = np.array(dish_center)

    def jiggle(self, dt):
        ang = np.random.uniform(0, 2 * PI)
        newpos = self.get_center() + 0.5 * dt * np.array([np.cos(ang), np.sin(ang), 0])
        while np.linalg.norm(newpos - self.dish_center) > CELL_BOUND:
            ang = np.random.uniform(0, 2 * PI)
            newpos = self.get_center() + 0.5 * dt * np.array([np.cos(ang), np.sin(ang), 0])
        self.move_to(newpos)

class PetriDishScene(Scene):
    def construct(self):
        rng = np.random.default_rng()

        dish_l_pos, dish_r_pos = LEFT * 3.5, RIGHT * 3.5
        dish_l = Circle(radius=DISH_R, color=GREY_E).move_to(dish_l_pos)
        dish_r = Circle(radius=DISH_R, color=GREY_E).move_to(dish_r_pos)
        
        lbl_l = Text("Azithromycin", color=BLUE, font_size=24).next_to(dish_l, UP)
        lbl_r = Text("Ciprofloxacin", color=GREEN, font_size=24).next_to(dish_r, UP)
        
        gen_tracker = ValueTracker(0)
        gen_num = always_redraw(
        lambda: Text(f"Generation: {int(gen_tracker.get_value())}", font_size=20)
            .to_edge(DOWN, buff=1)
        )

        pop_l_tracker = ValueTracker(START_POP)
        pop_l_count = always_redraw(
        lambda: Text(f"Pop: {int(pop_l_tracker.get_value())}", font_size=18)
            .next_to(dish_l, DOWN)
        )

        pop_r_tracker = ValueTracker(START_POP)
        pop_r_count = always_redraw(
        lambda: Text(f"Pop: {int(pop_r_tracker.get_value())}", font_size=18)
            .next_to(dish_r, DOWN)
        )

        self.add(dish_l, dish_r, lbl_l, lbl_r, gen_num, pop_l_count, pop_r_count)
        
        azi_cells = VGroup(*[BacterialCell(dish_l_pos + np.random.uniform(-1.5, 1.5, 3), dish_l_pos, color=BLUE) for _ in range(START_POP)])
        cip_cells = VGroup(*[BacterialCell(dish_r_pos + np.random.uniform(-1.5, 1.5, 3), dish_r_pos, color=GREEN) for _ in range(START_POP)])
        
        for c in [*azi_cells, *cip_cells]: 
            c.add_updater(lambda m, dt: m.jiggle(dt))
        
        self.play(FadeIn(azi_cells), FadeIn(cip_cells))
        self.wait(1)

        flash = Rectangle(
            width=config.frame_width, 
            height=config.frame_height, 
            fill_color=RED, 
            fill_opacity=0.15, 
            stroke_width=0
        )
        msg = Text("ANTIBIOTIC ADMINISTERED", color=RED, weight=BOLD, font_size=30)
        msg.add_background_rectangle(color=BLACK, opacity=0.8, buff=0.2)
        
        self.play(FadeIn(flash), Write(msg))
        self.play(FadeOut(flash), FadeOut(msg), run_time=0.8)

        p_azi = get_p_divide(C_TREAT, DATA["Azithromycin"]["alpha"], DATA["Azithromycin"]["beta"])
        p_cip = get_p_divide(C_TREAT, DATA["Ciprofloxacin"]["alpha"], DATA["Ciprofloxacin"]["beta"])

        for g in range(1, 41):
            gen_tracker.set_value(g)
            
            rem_a, par_a, kid_a = self.get_next_gen(azi_cells, p_azi, dish_l_pos, BLUE, rng)
            rem_c, par_c, kid_c = self.get_next_gen(cip_cells, p_cip, dish_r_pos, GREEN, rng)

            split_anims = []         
            
            def add_split_anims(parents, kids):
                for p_cell, k_cell in zip(parents, kids):
                    ang = rng.uniform(0, 2*PI)
                    offset = np.array([0.1 * np.cos(ang), 0.1 * np.sin(ang), 0])
                    split_anims.append(p_cell.animate.shift(-offset))
                    split_anims.append(FadeIn(k_cell, shift=offset, scale=0.5))
            add_split_anims(par_a, kid_a)
            add_split_anims(par_c, kid_c)

            if split_anims:
                self.play(*split_anims, run_time=0.4)
        
            azi_cells.add(*kid_a)
            cip_cells.add(*kid_c)

            self.wait(0.15) 

            death_anims = []
            death_anims.extend([FadeOut(c, scale=0.2) for c in rem_a])
            death_anims.extend([FadeOut(c, scale=0.2) for c in rem_c])

            new_pop_a = len(azi_cells) - len(rem_a)
            new_pop_c = len(cip_cells) - len(rem_c)

            if death_anims:
                self.play(
                    *death_anims,
                    pop_l_tracker.animate.set_value(new_pop_a),
                    pop_r_tracker.animate.set_value(new_pop_c),
                    run_time=0.4
                )
            else: 
                self.play(
                    pop_l_tracker.set_value(new_pop_a),
                    pop_r_tracker.set_value(new_pop_c),
                    run_time=0.1
                )

            azi_cells.remove(*rem_a)
            cip_cells.remove(*rem_c)
            
            self.wait(0.2)

            if len(azi_cells) == 0 and len(cip_cells) == 0:
                break

        self.wait(2)

    def get_next_gen(self, group, p, center, color, rng):
        to_remove = []
        parents = []
        kids = []
        for cell in group:
            if rng.random() < p:
                parents.append(cell)
                nc = BacterialCell(cell.get_center(), center, color=color)
                nc.add_updater(lambda m, dt: m.jiggle(dt))
                kids.append(nc)
            else:
                to_remove.append(cell)
                
        return to_remove, parents, kids