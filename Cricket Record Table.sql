USE Universal_Sports_Scoreboard_System;
Create TABLE Cricket_Match(
	Id INT auto_increment PRIMARY KEY,
    Match_Type VARCHAR(15) NOT NULL,
    Overs INTEGER(15) NOT NULL,
    Limited_over INTEGER(15) NOT NULL,
    Is_Started TINYINT NOT NULL DEFAULT 0,
    Is_Ended TINYINT NOT NULL DEFAULT 0,
    Created_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
SELECT * from Cricket_Match;